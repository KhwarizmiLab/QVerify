"""Depolarizing + readout noise for honest entanglement-based circuits."""

from __future__ import annotations

from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

_SINGLE_QUBIT_GATES = ("h", "x", "s", "sdg", "t", "tdg")


def build_honest_eb_noise_model(
    single_qubit_depol: float,
    two_qubit_depol: float,
    readout_prob: float,
) -> NoiseModel | None:
    """Return a :class:`~qiskit_aer.noise.NoiseModel` or ``None`` if all rates are zero."""
    if single_qubit_depol <= 0 and two_qubit_depol <= 0 and readout_prob <= 0:
        return None
    nm = NoiseModel()
    if single_qubit_depol > 0:
        e1 = depolarizing_error(single_qubit_depol, 1)
        nm.add_all_qubit_quantum_error(e1, list(_SINGLE_QUBIT_GATES))
    if two_qubit_depol > 0:
        e2 = depolarizing_error(two_qubit_depol, 2)
        nm.add_all_qubit_quantum_error(e2, ["cx"])
    if readout_prob > 0:
        p = min(max(readout_prob, 0.0), 0.5)
        ro = ReadoutError([[1.0 - p, p], [p, 1.0 - p]])
        nm.add_all_qubit_readout_error(ro)
    return nm
