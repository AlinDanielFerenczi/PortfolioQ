import os

# Set this in your environment before using a real IBM backend:
#   export IBM_QUANTUM_TOKEN="your_token_here"
IBM_QUANTUM_TOKEN = os.environ.get("IBM_QUANTUM_TOKEN")
IBM_QUANTUM_INSTANCE = os.environ.get("IBM_QUANTUM_INSTANCE")  # e.g. "ibm-q/open/main"