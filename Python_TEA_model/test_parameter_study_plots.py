import tempfile
import unittest
import warnings
import contextlib
import io
from pathlib import Path
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import MainCode
import parameter_study
from parameter_study_plots import METRIC_LABELS, plot_study, plot_workbook, select_metrics


class ParameterStudyPlotTests(unittest.TestCase):
    def test_numeric_grid_preserves_failed_case_gap_and_groups(self):
        frame = pd.DataFrame({
            "load": [3, 1, 2, 1, 2, 3],
            "mode": ["a", "a", "a", "b", "b", "b"],
            "LCOE_$/kWh": [3, 1, 2, 4, 5, 6],
            "error": [None, None, "failed", None, None, None],
        })
        figures = []
        original_subplots = plt.subplots

        def capture_figure(*args, **kwargs):
            fig, ax = original_subplots(*args, **kwargs)
            figures.append((fig, ax))
            return fig, ax

        with tempfile.TemporaryDirectory() as directory:
            with patch("parameter_study_plots.plt.subplots", side_effect=capture_figure):
                with self.assertWarnsRegex(UserWarning, "1 failed case"):
                    saved = plot_study(frame, "grid", ["load", "mode"], directory, ["LCOE_$/kWh"])
            self.assertEqual(len(saved), 1)
            self.assertTrue(saved[0].is_file())
            lines = figures[0][1].lines
            self.assertEqual(len(lines), 2)
            np.testing.assert_array_equal(lines[0].get_xdata(), [1, 2, 3])
            np.testing.assert_allclose(lines[0].get_ydata(), [1, np.nan, 3], equal_nan=True)
            self.assertEqual(lines[0].get_label(), "mode=a")

    def test_categorical_values_and_empty_metric(self):
        frame = pd.DataFrame({"mode": ["separate", "push-pull"], "geotes_max_hours": [10, 20]})
        with tempfile.TemporaryDirectory() as directory:
            saved = plot_study(frame, "mode", ["mode"], directory, ["geotes_max_hours"])
            self.assertTrue(saved[0].is_file())
            with self.assertWarnsRegex(UserWarning, "missing"):
                self.assertEqual(plot_study(frame, "mode", ["mode"], directory, ["LCOS"]), [])
            frame["geotes_max_hours"] = [np.nan, np.inf]
            with self.assertWarnsRegex(UserWarning, "no valid values"):
                self.assertEqual(plot_study(frame, "mode", ["mode"], directory, ["geotes_max_hours"]), [])

    def test_workbook_round_trip_and_metric_selection(self):
        self.assertEqual(select_metrics(["all"]), list(METRIC_LABELS))
        with self.assertRaisesRegex(ValueError, "Unknown plot metrics"):
            select_metrics(["wrong"])
        with tempfile.TemporaryDirectory() as directory:
            workbook = Path(directory) / "study.xlsx"
            pd.DataFrame({"qload": [100, 200], "LCOE_$/kWh": [0.1, 0.2]}).to_excel(workbook, index=False, sheet_name="load")
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                saved = plot_workbook(workbook, ["LCOE_$/kWh"])
            self.assertEqual(len(saved), 1)
            self.assertTrue(saved[0].is_file())
            self.assertEqual(saved[0].parent.name, "study_figures")

    def test_all_metrics_creates_one_plot_per_output(self):
        data = {"qload": [100, 200]}
        data.update({metric: [1, 2] for metric in METRIC_LABELS})
        with tempfile.TemporaryDirectory() as directory:
            saved = plot_study(pd.DataFrame(data), "all", ["qload"], directory, ["all"])
            self.assertEqual(len(saved), len(METRIC_LABELS))
            self.assertEqual(len(set(saved)), len(METRIC_LABELS))
            self.assertTrue(all(path.is_file() for path in saved))

    def test_new_study_saves_workbook_and_figures(self):
        frame = pd.DataFrame({
            "qload": [100, 200],
            "LCOE_$/kWh": [0.1, 0.2],
            "capacity_factor_%": [25, 30],
            "geotes_max_hours": [10, 20],
            "geotes_capacity_hours": [-1, 1],
        })
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(parameter_study.user_inputs, "output_dir", Path(directory)):
                with patch.object(parameter_study, "STUDIES", {"example": {"qload": [100, 200]}}):
                    with patch.object(parameter_study, "run_sweep", return_value=frame):
                        with patch.dict(parameter_study.user_inputs.system):
                            parameter_study.user_inputs.system["save_figs"] = True
                            parameter_study.main(["example"])
                            self.assertTrue(parameter_study.user_inputs.system["save_figs"])
            workbooks = list(Path(directory).glob("*.xlsx"))
            self.assertEqual(len(workbooks), 1)
            pd.testing.assert_frame_equal(pd.read_excel(workbooks[0]), frame)
            figures = list(workbooks[0].with_name(workbooks[0].stem + "_figures").glob("*.png"))
            self.assertEqual(len(figures), 4)

    def test_main_reports_when_figure_export_is_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(MainCode.user_inputs, "output_dir", Path(directory)):
                with patch.dict(MainCode.user_inputs.system, {"save_figs": False}):
                    with patch.object(MainCode, "initialize_plant"):
                        with patch.object(MainCode, "run_dispatch"):
                            with patch.object(MainCode, "calculate_costs"):
                                with patch.object(MainCode, "print_report"):
                                    with patch.object(MainCode, "export_report", return_value="report.xlsx"):
                                        with patch.object(MainCode, "export_figures") as export:
                                            output = io.StringIO()
                                            with contextlib.redirect_stdout(output):
                                                MainCode.main()
            export.assert_not_called()
            self.assertIn("Figure export disabled", output.getvalue())


if __name__ == "__main__":
    unittest.main()
