 Usage:
  # Run experiments once (CSVs saved automatically)
  python -m qverify_simulation.cli --output-dir
  results/

  # Later, regenerate figures with no simulation
  python -m qverify_simulation.cli --from-csv
  results/ --output-dir figures/