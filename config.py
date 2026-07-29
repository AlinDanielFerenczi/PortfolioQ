import os

from dotenv import load_dotenv

load_dotenv()

# Set these in your environment (or a .env file, see .env.example) before
# using a real IBM backend. Connects via the ibm_quantum_platform channel:
# TOKEN is an IBM Cloud API key, INSTANCE is your Quantum instance's CRN.
IBM_QUANTUM_TOKEN = os.environ.get("IBM_QUANTUM_TOKEN")
IBM_QUANTUM_INSTANCE = os.environ.get("IBM_QUANTUM_INSTANCE")