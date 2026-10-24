"""BOM, report and the pipeline CLI. No API key needed."""
import json
import subprocess
import sys

import pytest

from templates import build_design
from core.bom import make_bom, missing_lcsc, write_bom_csv
from tests.test_templates import DUAL, spec


def test_bom_groups_and_flags(tmp_path):
    design = build_design(spec(18), DUAL)
    bom = make_bom(design.netlist)
    assert sum(l.qty for l in bom.lines) == len(design.netlist.parts)
    caps100 = next(l for l in bom.lines if l.mpn == "CAP-ELEC-100UF-25V")
    assert caps100.qty == 3 and caps100.lcsc == "C44601"
    assert all(l.lcsc is None for l in missing_lcsc(bom))
    write_bom_csv(bom, tmp_path / "bom.csv")
    assert (tmp_path / "bom.csv").read_text().startswith("Refs,Qty,Value")


@pytest.mark.parametrize("name", ["dual_rail", "led_panel", "flasher", "ac_9v"])
def test_pipeline_examples_run_offline(name):
    res = subprocess.run([sys.executable, "-m", "pipeline", "--example", name],
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stdout + res.stderr
    netlist = json.loads(open(f"output/{name}/netlist.json").read())
    assert netlist["parts"]
