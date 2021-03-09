# pylint: disable=no-member
from unittest import mock_open, patch

import hypothesis.strategies as st
import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis.extra.numpy import arrays
from numpy.testing import assert_allclose

import xtgeo
from xtgeo.grid3d import Grid, GridProperty
from xtgeo.grid3d._gridprop_import_grdecl import open_grdecl, read_grdecl_3d_property


def create_grid(*args, **kwargs):
    grid = Grid()
    grid.create_box(*args, **kwargs)
    return grid


indecies = st.integers(min_value=4, max_value=12)
coordinates = st.floats(min_value=-100.0, max_value=100.0)
increments = st.floats(min_value=1.0, max_value=100.0)


grids = st.builds(
    create_grid,
    dimension=st.tuples(indecies, indecies, indecies),
    origin=st.tuples(coordinates, coordinates, coordinates),
    increment=st.tuples(increments, increments, increments),
    rotation=st.floats(min_value=0.0, max_value=90),
)


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(grids)
def test_grid_to_from_grdecl_file_is_identity(tmp_path, grid):
    filepath = tmp_path / "grid.grdecl"
    grid.to_file(filepath, fformat="grdecl")
    grid_from_file = Grid().from_file(filepath, fformat="grdecl")

    assert grid.dimensions == grid_from_file.dimensions
    assert np.array_equal(grid.actnum_array, grid_from_file.actnum_array)

    for prop1, prop_from_file in zip(
        grid.get_xyz_corners(), grid_from_file.get_xyz_corners()
    ):
        assert_allclose(
            prop1.get_npvalues1d(), prop_from_file.get_npvalues1d(), atol=1e-3
        )


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(grids)
def test_gridprop_to_from_file_is_identity(tmp_path, grid):
    filepath = tmp_path / "gridprop.grdecl"

    for prop in grid.get_xyz_corners():
        prop.to_file(filepath, fformat="grdecl")
        prop_from_file = GridProperty().from_file(
            filepath, name=prop.name, fformat="grdecl", grid=grid
        )

        assert_allclose(
            prop.get_npvalues1d(), prop_from_file.get_npvalues1d(), atol=1e-3
        )


@pytest.mark.parametrize(
    "file_data",
    [
        "PROP 1 2 3 4 / \n",
        "PROP\n 1 2 3 4 /",
        "PROP\n -- a comment \n 1 2 3 4 /",
        "-- a comment \n PROP\n \n 1 2 3 4 /",
        "PROP\n \n 1 2 \n -- a comment \n 3 4 /",
        "NOECHO \n PROP\n \n 1 2 \n -- a comment \n 3 4 /",
        "ECHO \n PROP\n \n 1 2 \n -- a comment \n 3 4 /",
        "NOECHO \n PROP\n \n 1 2 \n -- a comment \n 3 4 / \n ECHO",
    ],
)
def test_read_simple_property(file_data):
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        with open_grdecl(mock_file) as kw:
            assert list(kw) == [("PROP", ["1", "2", "3", "4"])]


@pytest.mark.parametrize(
    "undelimited_file_data",
    [
        "PROP 1 2 3 4 \n",
        "PROP\n 1 2 3 4 ECHO",
        "ECHO PROP\n 1 2 3 4",
        "PROP\n 1 2 3 4 -- a comment",
        "NOECHO PROP\n 1 2 3 4 -- a comment",
    ],
)
def test_read_raises_on_undelimited(undelimited_file_data):
    with patch(
        "builtins.open", mock_open(read_data=undelimited_file_data)
    ) as mock_file:
        with open_grdecl(mock_file) as kw:
            with pytest.raises(ValueError):
                list(kw)


@pytest.mark.parametrize(
    "file_data, shape, expected_value",
    [
        ("PROP 1 5 3 7 2 6 4 8 /\n", (2, 2, 2), [[[1, 2], [3, 4]], [[5, 6], [7, 8]]]),
        ("PROP 1 3 2 4 /\n", (1, 2, 2), [[[1, 2], [3, 4]]]),
    ],
)
def test_read_values_are_f_order(file_data, shape, expected_value):
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        np.array_equal(
            read_grdecl_3d_property(mock_file, "PROP", shape, int), expected_value
        )


@pytest.mark.parametrize(
    "file_data, shape",
    [
        ("NOPROP 1 5 3 7 2 6 4 8 /\n", (2, 2, 2)),
    ],
)
def test_read_values_raises_on_missing(file_data, shape):
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        with pytest.raises(xtgeo.KeywordNotFoundError):
            read_grdecl_3d_property(mock_file, "PROP", shape, int)


keywords = st.text(
    alphabet=st.characters(whitelist_categories=("Nd", "Lu")), min_size=1
)
grid_properties = arrays(
    elements=st.floats(), dtype="float", shape=st.tuples(indecies, indecies, indecies)
)


@given(keywords, grid_properties)
def test_read_write_grid_property_is_identity(keyword, grid_property):
    values = [str(v) for v in grid_property.flatten(order="F")]
    file_data = f"{keyword} {' '.join(values)} /"
    with patch("builtins.open", mock_open(read_data=file_data)) as mock_file:
        assert_allclose(
            read_grdecl_3d_property(mock_file, keyword, grid_property.shape),
            grid_property,
        )
