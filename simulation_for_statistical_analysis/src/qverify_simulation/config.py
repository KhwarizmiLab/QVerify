import math

CHSH_IDEAL = -2.0 * math.sqrt(2)
CHSH_REL_ERR_THRESHOLD_PCT = 10.0

# Honest EB (Aer) noise defaults: small depolarizing + readout error.
EB_NOISE_SINGLE_QUBIT_DEPOL = 0.0012
EB_NOISE_TWO_QUBIT_DEPOL = 0.006
EB_NOISE_READOUT_PROB = 0.008
