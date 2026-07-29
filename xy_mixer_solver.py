import math
from typing import List

import numpy as np
from scipy.optimize import minimize

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit.circuit import Parameter
from qiskit.circuit.library import RYGate
from qiskit_optimization.converters import QuadraticProgramToQubo

from config import IBM_QUANTUM_TOKEN, IBM_QUANTUM_INSTANCE


def build_dicke_circuit(n: int, k: int) -> QuantumCircuit:
    data = QuantumRegister(n, "data")

    if k == 0:
        return QuantumCircuit(data)
    if k == n:
        qc = QuantumCircuit(data)
        qc.x(data)
        return qc

    m = max(1, math.ceil(math.log2(k + 1)))
    anc = QuantumRegister(m, "cnt")
    qc = QuantumCircuit(data, anc)

    for i in range(n):
        remaining = n - i
        max_c = min(i, k)
        for c in range(max_c + 1):
            needed = k - c
            if needed < 0 or needed > remaining:
                continue
            p = needed / remaining
            if p <= 0:
                continue
            theta = 2 * math.asin(math.sqrt(min(p, 1.0)))
            if abs(theta) < 1e-12:
                continue
            gate = RYGate(theta).control(num_ctrl_qubits=m, ctrl_state=c, annotated=False)
            qc.append(gate, list(anc) + [data[i]])

        # controlled increment of the count register if data[i] == 1
        for j in reversed(range(m)):
            controls = [data[i]] + list(anc[0:j])
            qc.mcx(controls, anc[j])

    k_bits = format(k, f"0{m}b")[::-1]
    for j, bit in enumerate(k_bits):
        if bit == "1":
            qc.x(anc[j])

    return qc


def apply_cost_layer(qc: QuantumCircuit, data_qubits, hamiltonian, gamma):
    labels_coeffs = hamiltonian.to_list()
    for label, coeff in labels_coeffs:
        coeff = coeff.real
        z_positions = [i for i, ch in enumerate(reversed(label)) if ch == "Z"]
        if len(z_positions) == 1:
            qc.rz(2 * gamma * coeff, data_qubits[z_positions[0]])
        elif len(z_positions) == 2:
            i, j = z_positions
            qc.rzz(2 * gamma * coeff, data_qubits[i], data_qubits[j])
        elif len(z_positions) == 0:
            continue  # global phase, irrelevant
        else:
            raise ValueError("Unexpected higher-order term in portfolio QUBO Hamiltonian")


def apply_xy_mixer_layer(qc: QuantumCircuit, data_qubits, beta, topology: str = "ring"):
    n = len(data_qubits)
    if topology == "ring":
        edges = [(i, (i + 1) % n) for i in range(n)] if n > 2 else [(0, 1)]
    elif topology == "complete":
        edges = [(i, j) for i in range(n) for j in range(i + 1, n)]
    else:
        raise ValueError(f"Unknown mixer topology: {topology}")

    for i, j in edges:
        qc.rxx(2 * beta, data_qubits[i], data_qubits[j])
        qc.ryy(2 * beta, data_qubits[i], data_qubits[j])


def build_xy_qaoa_circuit(hamiltonian, n: int, k: int, reps: int, topology: str = "ring"):
    dicke = build_dicke_circuit(n, k)
    data_qubits = list(range(n))

    creg = ClassicalRegister(n, "meas")
    qc = QuantumCircuit(*dicke.qregs, creg)
    qc.compose(dicke, inplace=True)

    gammas = [Parameter(f"gamma_{p}") for p in range(reps)]
    betas = [Parameter(f"beta_{p}") for p in range(reps)]

    for p in range(reps):
        apply_cost_layer(qc, data_qubits, hamiltonian, gammas[p])
        apply_xy_mixer_layer(qc, data_qubits, betas[p], topology=topology)

    qc.measure(data_qubits, creg)
    return qc, gammas, betas


def _get_backend_and_sampler(backend_name: str):
    if backend_name == "aer_simulator":
        from qiskit_aer import AerSimulator
        backend = AerSimulator()
        from qiskit.primitives import BackendSamplerV2
        return backend, BackendSamplerV2(backend=backend)

    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    if not IBM_QUANTUM_TOKEN:
        raise RuntimeError(
            "IBM_QUANTUM_TOKEN not set. Export it to run on real hardware, "
            "or use backend='aer_simulator'."
        )
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform", token=IBM_QUANTUM_TOKEN, instance=IBM_QUANTUM_INSTANCE
    )
    backend = service.backend(backend_name)
    return backend, SamplerV2(mode=backend)


def solve_xy_qaoa(
    qp,
    tickers: List[str],
    budget: int,
    reps: int = 1,
    shots: int = 1024,
    backend_name: str = "aer_simulator",
    topology: str = "ring",
    maxiter: int = 100,
):
    min_maxiter = 2 * reps + 2
    if maxiter < min_maxiter:
        raise ValueError(
            f"maxiter={maxiter} is too low for reps={reps}: COBYLA needs at least "
            f"2*reps + 2 = {min_maxiter} function evaluations just to build its "
            "initial simplex before it can optimize anything."
        )

    n = len(tickers)
    converter = QuadraticProgramToQubo()
    qubo = converter.convert(qp)
    hamiltonian, offset = qubo.to_ising()

    circuit, gammas, betas = build_xy_qaoa_circuit(hamiltonian, n, budget, reps, topology)
    backend, sampler = _get_backend_and_sampler(backend_name)
    transpiled_template = transpile(circuit, backend=backend, optimization_level=1)

    op_counts = transpiled_template.count_ops()
    two_qubit_gates = sum(1 for instr in transpiled_template.data if len(instr.qubits) == 2)
    gate_info = {
        "total_gates": sum(op_counts.values()),
        "two_qubit_gates": two_qubit_gates,
        "circuit_depth": transpiled_template.depth(),
        "num_qubits": transpiled_template.num_qubits,
    }

    param_order = gammas + betas

    def run_and_get_counts(param_values, n_shots):
        bound = transpiled_template.assign_parameters(dict(zip(param_order, param_values)))
        job = sampler.run([bound], shots=n_shots)
        result = job.result()[0]
        return result.data.meas.get_counts()

    def expected_cost(param_values):
        counts = run_and_get_counts(param_values, shots)
        total = sum(counts.values())
        exp_val = 0.0
        for bitstring, count in counts.items():
            x = [int(b) for b in bitstring[::-1]]  # qiskit little-endian -> data[0..n-1]
            exp_val += qubo.objective.evaluate(x) * (count / total)
        return exp_val

    x0 = np.random.uniform(0, np.pi, size=2 * reps)
    opt_result = minimize(expected_cost, x0, method="COBYLA", options={"maxiter": maxiter})

    final_counts = run_and_get_counts(opt_result.x, max(shots, 2048))
    total = sum(final_counts.values())

    feasible_counts = {
        bs: c for bs, c in final_counts.items() if bs[::-1].count("1") == budget
    }
    feasible_fraction = sum(feasible_counts.values()) / total if total else 0.0

    # pick the most frequent feasible bitstring; if none were feasible
    # (shouldn't happen on a noiseless simulator, can happen on real noisy
    # hardware), fall back to the overall most frequent bitstring
    pool = feasible_counts if feasible_counts else final_counts
    best_bitstring = max(pool, key=pool.get)
    x = [int(b) for b in best_bitstring[::-1]]

    selected = [tickers[i] for i, b in enumerate(x) if b == 1]

    return {
        "selected_assets": selected,
        "bitstring": "".join(str(b) for b in x),
        "objective_value": float(qp.objective.evaluate(x)),
        "metadata": {
            "method": "xy_mixer_qaoa",
            "backend": backend_name,
            "reps": reps,
            "shots": shots,
            "mixer_topology": topology,
            "feasible_fraction": feasible_fraction,
            "optimizer_iterations": int(opt_result.get("nfev")),
            **gate_info,
        },
    }
