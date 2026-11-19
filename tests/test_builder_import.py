"""Test that the EasyEDA builder imports without EasyEDA running."""


def test_builder_imports():
    import easyeda.builder as b
    assert set(b.STAGES) >= {"parts", "sch", "erc", "pcb", "drc"}


def test_connectivity_module_imports():
    from easyeda.connectivity import check_connectivity
    assert callable(check_connectivity)