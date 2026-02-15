import unittest
from unittest.mock import patch, MagicMock, call

from graph import graph


def _summoner(tier="GOLD", rank="IV", lp=50):
    s = MagicMock()
    s.tier = tier
    s.rank = rank
    s.lp = lp
    return s


class TestGraph(unittest.TestCase):
    @patch("graph.plt")
    def test_plots_and_saves(self, mock_plt):
        records = [
            _summoner("GOLD", "IV", 50),
            _summoner("GOLD", "IV", 60),
            _summoner("GOLD", "IV", 70),
        ]
        graph(records)

        mock_plt.plot.assert_called_once()
        mock_plt.savefig.assert_called_once_with("graph.png")

    @patch("graph.plt")
    def test_plot_range_correct(self, mock_plt):
        records = [
            _summoner("GOLD", "IV", 50),
            _summoner("GOLD", "IV", 60),
        ]
        graph(records)

        args = mock_plt.plot.call_args[0]
        self.assertEqual(list(args[0]), [1, 2])

    @patch("graph.plt")
    def test_single_record(self, mock_plt):
        records = [_summoner("GOLD", "IV", 50)]
        graph(records)

        mock_plt.plot.assert_called_once()
        mock_plt.savefig.assert_called_once()


if __name__ == "__main__":
    unittest.main()
