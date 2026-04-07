import argparse
from pathlib import Path

from qverify_simulation.experiments.v1 import generate_figures_from_csv, generate_v1_pdfs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate relative-error PDF figures (fig1, fig2).")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("."),
        help="Directory for fig1_MeasureResend_vs_EB.pdf and fig2_V1_vs_EB.pdf",
    )
    parser.add_argument(
        "--from-csv",
        type=Path,
        default=None,
        metavar="DATA_DIR",
        help="Skip experiments; regenerate PDFs from err_*.csv files in DATA_DIR",
    )
    parser.add_argument(
        "--num-qubits",
        type=int,
        default=240,
        help=(
            "Pairs per run. Lower values increase finite-sample CHSH variance so "
            "honest EB relative-error histograms spread more (wider circuits are slower)."
        ),
    )
    parser.add_argument(
        "--shots",
        type=int,
        default=120,
        help="Shots per simulator run; increase for smoother histograms (slower).",
    )
    parser.add_argument(
        "--error-trials",
        type=int,
        default=4,
        help="Independent basis draws averaged for relative-error figures.",
    )
    parser.add_argument(
        "--no-save-csv",
        action="store_true",
        help="Do not save experiment results to CSV (ignored with --from-csv)",
    )
    parser.add_argument(
        "--no-eb-noise",
        action="store_true",
        help="Disable Aer depolarizing + readout noise on honest EB runs only.",
    )
    parser.add_argument(
        "--eb-noise-single",
        type=float,
        default=None,
        metavar="P",
        help="1-qubit depolarizing probability per gate (default from config).",
    )
    parser.add_argument(
        "--eb-noise-two-qubit",
        type=float,
        default=None,
        metavar="P",
        help="2-qubit depolarizing probability per CX (default from config).",
    )
    parser.add_argument(
        "--eb-noise-readout",
        type=float,
        default=None,
        metavar="P",
        help="Symmetric classical readout error probability (default from config).",
    )
    args = parser.parse_args()

    if args.from_csv is not None:
        generate_figures_from_csv(data_dir=args.from_csv, output_dir=args.output_dir)
    else:
        generate_v1_pdfs(
            output_dir=args.output_dir,
            num_qubits=args.num_qubits,
            shots=args.shots,
            error_trials=args.error_trials,
            save_csv=not args.no_save_csv,
            eb_noise=not args.no_eb_noise,
            eb_noise_single=args.eb_noise_single,
            eb_noise_two_qubit=args.eb_noise_two_qubit,
            eb_noise_readout=args.eb_noise_readout,
        )


if __name__ == "__main__":
    main()
