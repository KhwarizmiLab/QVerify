from pathlib import Path

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit_aer.noise import NoiseModel

from qverify_simulation.config import (
    EB_NOISE_READOUT_PROB,
    EB_NOISE_SINGLE_QUBIT_DEPOL,
    EB_NOISE_TWO_QUBIT_DEPOL,
)
from qverify_simulation.figures.relative_error_pdf import (
    aligned_layout,
    plot_fig1_imr,
    plot_fig2_v1,
)
from qverify_simulation.io.csv_io import load_distributions, save_distributions
from qverify_simulation.simulation.backend import sim_circuits
from qverify_simulation.simulation.circuits import (
    alice_measurement_choices,
    apply_basis,
    apply_basis_Eve,
    apply_measurement,
    bob_measurement_choices,
    create_singlets,
    entanglment_basis_mapB,
    eve_encode,
    get_result,
    measure_cir,
)
from qverify_simulation.simulation.eb_noise import build_honest_eb_noise_model
from qverify_simulation.statistics.distributions import (
    average_and_normalize_probabilities,
    compute_error_dist_eb,
    compute_error_dist_pm,
)


def _resolve_eb_noise_model(
    enabled: bool,
    single: float | None,
    two_q: float | None,
    readout: float | None,
) -> NoiseModel | None:
    if not enabled:
        return None
    s = EB_NOISE_SINGLE_QUBIT_DEPOL if single is None else single
    t = EB_NOISE_TWO_QUBIT_DEPOL if two_q is None else two_q
    r = EB_NOISE_READOUT_PROB if readout is None else readout
    return build_honest_eb_noise_model(s, t, r)


def run_exp(num_qubits, BA, BB, shots=1, eb_noise_model: NoiseModel | None = None):
    qc, qrA, qrB, crA, crB = create_singlets(num_qubits)
    qc = apply_basis(num_qubits, qc, qrA, qrB, BA, BB)
    qc = apply_measurement(num_qubits, qc, qrA, qrB, crA, crB)
    res = sim_circuits(qc, shots=shots, noise_model=eb_noise_model)
    return qc, res


def run_attackexp_V1(num_qubits, BA, BB, shots=1):
    qc, qrA, qrB, crA, crB = create_singlets(num_qubits)
    qc = apply_basis_Eve(num_qubits, qc, qrA, qrB, BA)
    qc = apply_measurement(num_qubits, qc, qrA, qrB, crA, crB)
    RA, RE = get_result(qc)
    qr2, crB2, quantum_channel = eve_encode(num_qubits, BA, RE)
    for i in range(num_qubits):
        quantum_channel = entanglment_basis_mapB[BB[i]](quantum_channel, qr2, i)
    for i in range(num_qubits):
        quantum_channel = measure_cir(quantum_channel, qr2, crB2, i)
    res2 = sim_circuits(quantum_channel, shots=shots)
    return RA, res2, quantum_channel


def run_attack_imr(num_qubits, BA, BB, shots=1):
    qc, qrA, qrB, crA, crB = create_singlets(num_qubits)
    qc = apply_basis(num_qubits, qc, qrA, qrB, BA, [2] * num_qubits)
    qc = apply_measurement(num_qubits, qc, qrA, qrB, crA, crB)
    RA, RE = get_result(qc)
    qr2 = QuantumRegister(num_qubits, name="qr2")
    crB2 = ClassicalRegister(num_qubits, name="crB2")
    qc2 = QuantumCircuit(qr2, crB2)
    for i in range(num_qubits):
        if RE[i] == "1":
            qc2.x(qr2[i])
    for i in range(num_qubits):
        qc2 = entanglment_basis_mapB[BB[i]](qc2, qr2, i)
    for i in range(num_qubits):
        qc2 = measure_cir(qc2, qr2, crB2, i)
    res2 = sim_circuits(qc2, shots=shots)
    return RA, res2


def build_relative_error_distributions(
    num_qubits: int,
    shots: int,
    n_trials: int = 4,
    eb_noise_model: NoiseModel | None = None,
):
    err_eb_all = []
    err_imr_all = []
    err_v1_all = []
    for _ in range(n_trials):
        BA = alice_measurement_choices(num_qubits)
        BB = bob_measurement_choices(num_qubits)
        _, res_eb = run_exp(num_qubits, BA, BB, shots=shots, eb_noise_model=eb_noise_model)
        err_eb_all.append(compute_error_dist_eb(res_eb, BA, BB, num_qubits))
        RA_imr, res_imr = run_attack_imr(num_qubits, BA, BB, shots=shots)
        err_imr_all.append(compute_error_dist_pm(res_imr, RA_imr, BA, BB, num_qubits))
        RA_v1, res_v1, _ = run_attackexp_V1(num_qubits, BA, BB, shots=shots)
        err_v1_all.append(compute_error_dist_pm(res_v1, RA_v1, BA, BB, num_qubits))
    err_eb_final = average_and_normalize_probabilities(*err_eb_all)
    err_imr_final = average_and_normalize_probabilities(*err_imr_all)
    err_v1_final = average_and_normalize_probabilities(*err_v1_all)
    return err_eb_final, err_imr_final, err_v1_final


def _render_pdfs(
    out: Path,
    err_eb: dict,
    err_imr: dict,
    err_v1: dict,
) -> None:
    bw_u, yl_hi = aligned_layout(err_imr, err_v1, err_eb)
    plot_fig1_imr(err_imr, err_eb, output_file=str(out / "fig1_MeasureResend_vs_EB.pdf"),
                  bar_w_u=bw_u, y_lim_hi=yl_hi)
    plot_fig2_v1(err_v1, err_eb, output_file=str(out / "fig2_V1_vs_EB.pdf"),
                 bar_w_u=bw_u, y_lim_hi=yl_hi)


def generate_v1_pdfs(
    output_dir: str | Path,
    num_qubits: int = 240,
    shots: int = 120,
    error_trials: int = 4,
    save_csv: bool = True,
    eb_noise: bool = True,
    eb_noise_single: float | None = None,
    eb_noise_two_qubit: float | None = None,
    eb_noise_readout: float | None = None,
) -> None:
    """Run experiments, optionally save results to CSV, and render PDFs.

    Default ``num_qubits`` is moderate so the CHSH estimate per shot has enough
    finite-sampling noise that honest EB relative-error distributions show
    visible spread (very large ``num_qubits`` pins S near Tsirelson and looks
    almost deterministic). For tighter EB peaks or publication runs, increase
    ``num_qubits`` and ``shots``.

    When ``eb_noise`` is true (default), honest EB uses a small Aer depolarizing
    + readout noise model (see :mod:`qverify_simulation.config`); attacks stay
    noiseless unless you extend the experiment code.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    eb_nm = _resolve_eb_noise_model(
        eb_noise, eb_noise_single, eb_noise_two_qubit, eb_noise_readout
    )
    err_eb, err_imr, err_v1 = build_relative_error_distributions(
        num_qubits, shots, n_trials=error_trials, eb_noise_model=eb_nm
    )
    if save_csv:
        save_distributions(out, err_eb, err_imr, err_v1)
    _render_pdfs(out, err_eb, err_imr, err_v1)


def generate_figures_from_csv(
    data_dir: str | Path,
    output_dir: str | Path | None = None,
) -> None:
    """Regenerate PDFs from previously saved CSV files (no experiments run).

    Args:
        data_dir: Directory containing ``err_eb.csv``, ``err_imr.csv``, and
            ``err_v1.csv`` produced by :func:`generate_v1_pdfs` with
            ``save_csv=True``.
        output_dir: Where to write the PDFs.  Defaults to *data_dir*.
    """
    data_dir = Path(data_dir)
    out = Path(output_dir) if output_dir is not None else data_dir
    out.mkdir(parents=True, exist_ok=True)
    err_eb, err_imr, err_v1 = load_distributions(data_dir)
    _render_pdfs(out, err_eb, err_imr, err_v1)
