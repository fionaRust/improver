# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2020 Met Office.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""Unit tests for nbhood.ApplyNeighbourhoodProcessingWithAMask."""

import unittest
from collections import OrderedDict

import iris
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal
from iris.coords import DimCoord

from improver.nbhood.use_nbhood import ApplyNeighbourhoodProcessingWithAMask

from ..nbhood.test_BaseNeighbourhoodProcessing import set_up_cube
from ...set_up_test_cubes import (
    set_up_variable_cube,
    set_up_probability_cube,
    add_coordinate,
)


class Test__init__(unittest.TestCase):

    """Test the __init__ method of ApplyNeighbourhoodProcessingWithAMask."""

    def test_basic(self):
        """Test that the __init__ method returns the expected string."""
        coord_for_masking = "topographic_zone"
        radii = 2000
        result = ApplyNeighbourhoodProcessingWithAMask(coord_for_masking, radii)
        msg = (
            "<ApplyNeighbourhoodProcessingWithAMask: coord_for_masking: "
            "topographic_zone, neighbourhood_method: square, radii: 2000, "
            "lead_times: None, collapse_weights: None, weighted_mode: True, "
            "sum_or_fraction: fraction, re_mask: False>"
        )
        self.assertEqual(str(result), msg)


class Test__repr__(unittest.TestCase):

    """Test the __repr__ method of ApplyNeighbourhoodProcessingWithAMask."""

    def test_basic(self):
        """Test that the __repr__ method returns the expected string."""
        coord_for_masking = "topographic_zone"
        radii = 2000
        result = str(ApplyNeighbourhoodProcessingWithAMask(coord_for_masking, radii))
        msg = (
            "<ApplyNeighbourhoodProcessingWithAMask: coord_for_masking: "
            "topographic_zone, neighbourhood_method: square, radii: 2000, "
            "lead_times: None, collapse_weights: None, weighted_mode: True, "
            "sum_or_fraction: fraction, re_mask: False>"
        )
        self.assertEqual(result, msg)


class Test_collapse_mask_coord(unittest.TestCase):
    """
    Test the collapse_mask_coord method.
    Although the normalisation of any weights isn't done explicitly in this
    function we want to test that the normalisation functionality in the
    underlying functions is suitable for the cases we need to handle in
    this plugin.
    """

    def setUp(self):
        """Set up a simple cube to collapse"""
        # A simplified example of neighbourhood processed data for a set of
        # topographic bands for a single threshold.
        data = np.array(
            [
                [[1, 1, 0,], [1, 1, 0,], [0, 0, 0,],],
                [[0, 0, 1,], [0, 1, 1,], [1, 1, 0,],],
                [[0, 0, 0,], [0, 0, 0,], [0, 0, 1,],],
            ],
            dtype=np.float32,
        )
        cube = set_up_probability_cube(
            np.ones((1, 3, 3), dtype=np.float32), [278.15], spatial_grid="equalarea",
        )
        self.cube = add_coordinate(cube, [50, 100, 150], "topographic_zone", "m")
        self.cube = iris.util.squeeze(self.cube)
        self.cube.data = data
        # Set up weights cubes
        weights_data = np.array(
            [
                [[1, 1, 0,], [1, 0.5, 0,], [0, 0, 0,],],
                [[0, 0, 1,], [0, 0.5, 0.75,], [1, 0.75, 0.5,],],
                [[0, 0, 0,], [0, 0, 0.25,], [0, 0.25, 0.5,],],
            ],
            dtype=np.float32,
        )
        cube = set_up_variable_cube(
            np.ones((3, 3), dtype=np.float32),
            name="topographic_zone_weights",
            units="1",
            spatial_grid="equalarea",
        )
        self.weights_cube = add_coordinate(
            cube, [50, 100, 150], "topographic_zone", "m"
        )
        self.weights_cube.data = weights_data

    def test_basic(self):
        """Test we get a the expected reult with a simple collapse"""
        expected_data = np.array(
            [[1.0, 1.0, 1.0], [1.0, 1.0, 0.75], [1.0, 0.75, 0.5]], dtype=np.float32
        )
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin.collapse_mask_coord(self.cube)
        assert_allclose(result.data, expected_data)
        self.assertNotIn("topographic_zone", result.coords())

    def test_renormalise_when_missing_data(self):
        """
        Test we get a the expected reult when the weights need renormalising
        to account for missing data that comes from neighbourhood processing
        where there are no points to process in a given band for a given point.
        The expected behaviour is that the weights are renormalised and the
        result for that point takes 100% of the band with a valid value in.
        """
        data = np.array(
            [
                [[1, 1, 0,], [1, 1, 0,], [0, 0, 0,],],
                [[0, 0, 1,], [0, 1, 1,], [1, 1, 0,],],
                [[0, 0, 0,], [0, 0, 0,], [0, 0, np.nan,],],
            ],
            dtype=np.float32,
        )
        self.cube.data = data
        expected_data = np.array(
            [[1.0, 1.0, 1.0], [1.0, 1.0, 0.75], [1.0, 0.75, 0]], dtype=np.float32
        )
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin.collapse_mask_coord(self.cube)
        assert_allclose(result.data, expected_data)
        self.assertNotIn("topographic_zone", result.coords())

    def test_masked_weights_data(self):
        """Test points where weights are masked.
           Covers the case where sea points may be masked out so
           they aren't neighbourhood processed."""
        self.weights_cube.data[:, 0, 0] = np.nan
        self.weights_cube.data = np.ma.masked_invalid(self.weights_cube.data)
        expected_data = np.array(
            [[np.nan, 1.0, 1.0], [1.0, 1.0, 0.75], [1.0, 0.75, 0.5]], dtype=np.float32
        )
        expected_mask = np.array(
            [[True, False, False], [False, False, False], [False, False, False]]
        )
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin.collapse_mask_coord(self.cube)
        assert_allclose(result.data.data, expected_data)
        assert_allclose(result.data.mask, expected_mask)
        self.assertNotIn("topographic_zone", result.coords())

    def test_masked_weights_and_missing(self):
        """Test masked weights, and one point has nan in from
           neighbourhood processing.
           Covers the case where sea points may be masked out so
           they aren't neighbourhood processed. The nan point comes
           from neighbourhood processing where it has found no points to
           process for a given point in a given band."""
        self.weights_cube.data[:, 0, 0] = np.nan
        self.weights_cube.data = np.ma.masked_invalid(self.weights_cube.data)
        self.cube.data[2, 2, 2] = np.nan
        expected_data = np.array(
            [[np.nan, 1.0, 1.0], [1.0, 1.0, 0.75], [1.0, 0.75, 0.0]], dtype=np.float32
        )
        expected_mask = np.array(
            [[True, False, False], [False, False, False], [False, False, False]]
        )
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin.collapse_mask_coord(self.cube)
        assert_allclose(result.data.data, expected_data)
        assert_allclose(result.data.mask, expected_mask)
        self.assertNotIn("topographic_zone", result.coords())


class Test_process(unittest.TestCase):

    """Test the process method of ApplyNeighbourhoodProcessingWithAMask."""

    def setUp(self):
        """
        Set up a cube with a single threshold to be processed and corresponding
        mask and weights cubes.
        """
        data = np.array([[[1, 1, 1,], [1, 1, 0,], [0, 0, 0,],],], dtype=np.float32,)
        self.cube = set_up_probability_cube(data, [278.15], spatial_grid="equalarea",)

        # Set up mask cube. Currently mask cubes have sea points set to zero,
        # not masked out.
        mask_data = np.array(
            [
                [[0, 1, 0,], [1, 1, 0,], [0, 0, 0,],],
                [[0, 0, 1,], [0, 0, 1,], [1, 1, 0,],],
                [[0, 0, 0,], [0, 0, 0,], [0, 0, 1,],],
            ],
            dtype=np.float32,
        )
        cube = set_up_variable_cube(
            np.ones((3, 3), dtype=np.float32),
            name="topographic_zone_weights",
            units="1",
            spatial_grid="equalarea",
        )
        self.mask_cube = add_coordinate(cube, [50, 100, 150], "topographic_zone", "m")
        self.mask_cube.data = mask_data

        # Set up weights cubes, with one masked sea point. Currently only
        # weights cubes have masked out sea points.
        weights_data = np.array(
            [
                [[np.nan, 1, 0,], [1, 0.5, 0,], [0, 0, 0,],],
                [[np.nan, 0, 1,], [0, 0.5, 0.75,], [0.75, 0.75, 0.5,],],
                [[np.nan, 0, 0,], [0, 0, 0.25,], [0.25, 0.25, 0.5,],],
            ],
            dtype=np.float32,
        )
        weights_data = np.ma.masked_invalid(weights_data)
        cube = set_up_variable_cube(
            np.ones((3, 3), dtype=np.float32),
            name="topographic_zone_weights",
            units="1",
            spatial_grid="equalarea",
        )
        self.weights_cube = add_coordinate(
            cube, [50, 100, 150], "topographic_zone", "m"
        )
        self.weights_cube.data = weights_data

        # Set all cubes to have the same 2km spaced x and y coords.
        for cube in [self.cube, self.mask_cube, self.weights_cube]:
            cube.coord("projection_x_coordinate").points = np.array(
                [0, 2000, 4000], dtype=np.float32
            )
            cube.coord("projection_y_coordinate").points = np.array(
                [0, 2000, 4000], dtype=np.float32
            )

    def test_basic_no_collapse(self):
        """Test process for a cube with 1 threshold and no collapse.
        This test shows the result of neighbourhood processing the same input
        data three times with the three different masks for the different
        topographic zones."""
        plugin = ApplyNeighbourhoodProcessingWithAMask("topographic_zone", 2000)
        result = plugin(self.cube, self.mask_cube)
        expected_result = np.array(
            [
                [
                    [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0],],
                    [[np.nan, 0.5, 0.5], [0.0, 0.25, 0.33333334], [0.0, 0.0, 0.0],],
                    [[np.nan, np.nan, np.nan], [np.nan, 0.0, 0.0], [np.nan, 0.0, 0.0],],
                ],
            ],
            dtype=np.float32,
        )
        assert_allclose(result.data, expected_result, equal_nan=True)

    def test_basic_collapse(self):
        """Test process for a cube with 1 threshold and collapsing the topographic_zones.
        This test shows the result of neighbourhood processing the same input
        data three times with the three different masks for the different
        topographic zones, then doing a weighted collapse of the topopgraphic
        band taking into account any missing data."""
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin(self.cube, self.mask_cube)
        expected_result = np.array(
            [[[np.nan, 1.0, 0.5], [1.0, 0.625, 0.25], [0.0, 0.0, 0.0]]],
            dtype=np.float32,
        )
        expected_result = np.ma.masked_invalid(expected_result)
        assert_allclose(result.data.data, expected_result.data, equal_nan=True)
        assert_array_equal(result.data.mask, expected_result.mask)

    def test_no_collapse_multithreshold(self):
        """Test process for a cube with 2 thresholds and no collapse.
        Same data as test_basic_no_collapse with an extra point in the leading
        threshold dimension"""
        cube2 = self.cube.copy()
        cube2.coord("air_temperature").points = np.array([273.15], dtype=np.float32)
        multi_threshold_cube = iris.cube.CubeList([cube2, self.cube]).concatenate_cube()
        plugin = ApplyNeighbourhoodProcessingWithAMask("topographic_zone", 2000)
        result = plugin(multi_threshold_cube, self.mask_cube)
        expected_result = np.array(
            [
                [
                    [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0],],
                    [[np.nan, 0.5, 0.5], [0.0, 0.25, 0.33333334], [0.0, 0.0, 0.0],],
                    [[np.nan, np.nan, np.nan], [np.nan, 0.0, 0.0], [np.nan, 0.0, 0.0],],
                ],
                [
                    [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0],],
                    [[np.nan, 0.5, 0.5], [0.0, 0.25, 0.33333334], [0.0, 0.0, 0.0],],
                    [[np.nan, np.nan, np.nan], [np.nan, 0.0, 0.0], [np.nan, 0.0, 0.0],],
                ],
            ],
            dtype=np.float32,
        )
        assert_allclose(result.data, expected_result, equal_nan=True)

    def test_collapse_multithreshold(self):
        """Test process for a cube with 2 thresholds and collapsing the topographic_zones.
        Same data as test_basic_collapse with an extra point in the leading
        threshold dimension"""
        cube2 = self.cube.copy()
        cube2.coord("air_temperature").points = np.array([273.15], dtype=np.float32)
        multi_threshold_cube = iris.cube.CubeList([cube2, self.cube]).concatenate_cube()
        plugin = ApplyNeighbourhoodProcessingWithAMask(
            "topographic_zone", 2000, collapse_weights=self.weights_cube
        )
        result = plugin(multi_threshold_cube, self.mask_cube)
        expected_result = np.array(
            [
                [[np.nan, 1.0, 0.5], [1.0, 0.625, 0.25], [0.0, 0.0, 0.0]],
                [[np.nan, 1.0, 0.5], [1.0, 0.625, 0.25], [0.0, 0.0, 0.0]],
            ],
            dtype=np.float32,
        )
        expected_result = np.ma.masked_invalid(expected_result)
        assert_allclose(result.data.data, expected_result.data, equal_nan=True)
        assert_array_equal(result.data.mask, expected_result.mask)


if __name__ == "__main__":
    unittest.main()
