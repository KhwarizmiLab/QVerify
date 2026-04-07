from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel


def sim_circuits(
    circuit,
    shots: int = 1,
    noise_model: NoiseModel | None = None,
) -> dict[str, float]:
    opts: dict = {"method": "matrix_product_state"}
    if noise_model is not None:
        opts["noise_model"] = noise_model
    sim = AerSimulator(**opts)
    job = sim.run(circuit, shots=shots)
    results = job.result().get_counts()
    return {key: value / shots for key, value in results.items()}
