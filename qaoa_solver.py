from qiskit_algorithms import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.converters import QuadraticProgramToQubo
from qiskit.circuit.library import QAOAAnsatz
from qiskit import transpile

from qiskit.primitives import SamplerPub
from config import IBM_QUANTUM_TOKEN, IBM_QUANTUM_INSTANCE
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


class TranspilingSampler:
    def __init__(self, inner_sampler, backend):
        self._inner = inner_sampler
        self._backend = backend

    def run(self, pubs, *, shots=None):
        new_pubs = []
        for pub in pubs:
            coerced = SamplerPub.coerce(pub, shots)
            transpiled_circuit = transpile(coerced.circuit, backend=self._backend, optimization_level=1)
            new_pubs.append((transpiled_circuit, coerced.parameter_values, coerced.shots))
        return self._inner.run(new_pubs, shots=shots)


def _get_sampler(backend_name: str, shots: int):
    if backend_name == "aer_simulator":
        from qiskit_aer import AerSimulator
        from qiskit.primitives import BackendSamplerV2

        backend = AerSimulator()
        raw_sampler = BackendSamplerV2(backend=backend)
        return TranspilingSampler(raw_sampler, backend), backend

    if not IBM_QUANTUM_TOKEN:
        raise RuntimeError(
            "IBM_QUANTUM_TOKEN not set. Export it in your environment to run "
            "against real hardware, or use backend='aer_simulator' for the "
            "noiseless baseline."
        )
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=IBM_QUANTUM_TOKEN, instance=IBM_QUANTUM_INSTANCE
    )
    backend = service.backend(backend_name)
    raw_sampler = SamplerV2(mode=backend)
    return TranspilingSampler(raw_sampler, backend), backend


def _estimate_gate_counts(qubo, reps: int, backend=None):
    hamiltonian, _ = qubo.to_ising()
    ansatz = QAOAAnsatz(cost_operator=hamiltonian, reps=reps)

    if backend is not None:
        transpiled = transpile(ansatz, backend=backend, optimization_level=1)
    else:
        transpiled = transpile(ansatz, basis_gates=["cx", "rz", "sx", "x"], optimization_level=1)

    op_counts = transpiled.count_ops()
    two_qubit_gates = sum(1 for instr in transpiled.data if len(instr.qubits) == 2)
    return {
        "total_gates": sum(op_counts.values()),
        "two_qubit_gates": two_qubit_gates,
        "circuit_depth": transpiled.depth(),
        "num_qubits": transpiled.num_qubits,
    }


def solve_qaoa(
    qp,
    tickers: list,
    reps: int = 1,
    shots: int = 1024,
    backend_name: str = "aer_simulator",
    maxiter: int = 100,
):
    min_maxiter = 2 * reps + 2
    if maxiter < min_maxiter:
        raise ValueError(
            f"maxiter={maxiter} is too low for reps={reps}: COBYLA needs at least "
            f"2*reps + 2 = {min_maxiter} function evaluations just to build its "
            "initial simplex before it can optimize anything."
        )

    converter = QuadraticProgramToQubo()
    qubo = converter.convert(qp)

    sampler, backend = _get_sampler(backend_name, shots)
    gate_info = _estimate_gate_counts(qubo, reps, backend)

    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps)
    optimizer = MinimumEigenOptimizer(qaoa)
    result = optimizer.solve(qp)

    x = result.x
    bitstring = "".join(str(int(b)) for b in x)
    selected = [tickers[i] for i, b in enumerate(x) if b > 0.5]

    return {
        "selected_assets": selected,
        "bitstring": bitstring,
        "objective_value": float(result.fval),
        "metadata": {
            "method": "qaoa",
            "backend": backend_name,
            "reps": reps,
            "shots": shots,
            "maxiter": maxiter,
            **gate_info,
        },
    }
