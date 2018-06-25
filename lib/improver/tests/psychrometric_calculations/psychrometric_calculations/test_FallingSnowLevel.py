# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2018 Met Office.
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
"""Unit tests for psychrometric_calculations FallingSnowLevel."""

import unittest

import numpy as np

from cf_units import Unit
import iris
from iris.tests import IrisTest

from improver.psychrometric_calculations.psychrometric_calculations import (
    FallingSnowLevel)
from improver.tests.ensemble_calibration.ensemble_calibration.\
    helper_functions import set_up_cube
from improver.tests.utilities.test_mathematical_operations import (
    set_up_height_cube)


class Test__repr__(IrisTest):

    """Test the repr method."""

    def test_basic(self):
        """Test that the __repr__ returns the expected string."""
        result = str(FallingSnowLevel())
        msg = ('<FallingSnowLevel: '
               'precision:0.005, falling_level_threshold:90.0>')
        self.assertEqual(result, msg)


class Test_find_falling_level(IrisTest):

    """Test the find_falling_level method."""

    def setUp(self):
        """Set up arrays."""
        self.wb_int_data = np.array([[[80.0, 80.0], [70.0, 50.0]],
                                     [[90.0, 100.0], [80.0, 60.0]],
                                     [[100.0, 110.0], [90.0, 100.0]]])

        self.orog_data = np.array([[0.0, 0.0], [5.0, 3.0]])
        self.height_points = np.array([5.0, 10.0, 20.0])

    def test_basic(self):
        """Test method returns an array with correct data"""
        plugin = FallingSnowLevel()
        expected = np.array([[10.0, 7.5], [25.0, 20.5]])
        result = plugin.find_falling_level(
            self.wb_int_data, self.orog_data, self.height_points)
        self.assertIsInstance(result, np.ndarray)
        self.assertArrayEqual(result, expected)

    def test_outside_range(self):
        """Test method returns an nan if data outside range"""
        plugin = FallingSnowLevel()
        wb_int_data = self.wb_int_data
        wb_int_data[2, 1, 1] = 70.0
        result = plugin.find_falling_level(
            wb_int_data, self.orog_data, self.height_points)
        self.assertTrue(np.isnan(result[1, 1]))


class Test_fill_in_high_snow_falling_levels(IrisTest):

    """Test the fill_in_high_snow_falling_levels method."""

    def setUp(self):
        """ Set up arrays for testing."""
        self.snow_level_data = np.array([[1.0, 1.0, 2.0],
                                         [1.0, np.nan, 2.0],
                                         [1.0, 2.0, 2.0]])
        self.snow_data_no_interp = np.array([[np.nan, np.nan, np.nan],
                                             [1.0, np.nan, 2.0],
                                             [1.0, 2.0, np.nan]])
        self.orog = np.ones((3, 3))
        self.highest_wb_int = np.ones((3, 3))
        self.highest_height = 300.0

    def test_basic(self):
        """Test fills in missing data with orography + highest height"""
        plugin = FallingSnowLevel()
        self.highest_wb_int[1, 1] = 100.0
        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, 301.0, 2.0],
                             [1.0, 2.0, 2.0]])
        plugin.fill_in_high_snow_falling_levels(
            self.snow_level_data, self.orog, self.highest_wb_int,
            self.highest_height)
        self.assertArrayEqual(self.snow_level_data, expected)

    def test_no_fill_if_conditions_not_met(self):
        """Test it doesn't fill in NaN if the heighest wet bulb integral value
           is less the than threshold."""
        plugin = FallingSnowLevel()
        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, np.nan, 2.0],
                             [1.0, 2.0, 2.0]])
        plugin.fill_in_high_snow_falling_levels(
            self.snow_level_data, self.orog, self.highest_wb_int,
            self.highest_height)
        self.assertArrayEqual(self.snow_level_data, expected)


class Test_fill_sea_points(IrisTest):

    """Test the fill_in_missing_data method."""

    def setUp(self):
        """ Set up arrays for testing."""
        self.snow_level_data = np.array([[1.0, 1.0, 2.0],
                                         [1.0, np.nan, 2.0],
                                         [1.0, 2.0, 2.0]])
        self.wb_int = np.array([[100.0, 100.0, 100.0],
                                [100.0, 5.0, 100.0],
                                [100.0, 100.0, 100.0]])
        self.land_sea = np.ones((3, 3))

    def test_basic(self):
        """Test it fills in the points it's meant to."""
        plugin = FallingSnowLevel()
        self.land_sea[1, 1] = 0

        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, 0, 2.0],
                             [1.0, 2.0, 2.0]])
        plugin.fill_in_sea_points(self.snow_level_data, self.land_sea,
                                  self.wb_int)
        self.assertArrayEqual(self.snow_level_data, expected)

    def test_no_sea(self):
        """Test it only fills in sea points, and ignores a land point"""
        plugin = FallingSnowLevel()
        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, np.nan, 2.0],
                             [1.0, 2.0, 2.0]])
        plugin.fill_in_sea_points(self.snow_level_data, self.land_sea,
                                  self.wb_int)
        self.assertArrayEqual(self.snow_level_data, expected)

    def test_all_above_threshold(self):
        """Test it doesn't change points that are all above the threshold"""
        plugin = FallingSnowLevel()
        self.wb_int[1, 1] = 100
        self.snow_level_data[1, 1] = 1.0

        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, 1.0, 2.0],
                             [1.0, 2.0, 2.0]])
        plugin.fill_in_sea_points(self.snow_level_data, self.land_sea,
                                  self.wb_int)
        self.assertArrayEqual(self.snow_level_data, expected)


class Test_fill_in_by_horizontal_interpolation(IrisTest):
    """Test the fill_in_by_horizontal_interpolation method"""
    def setUp(self):
        """ Set up arrays for testing."""
        self.snow_level_data = np.array([[1.0, 1.0, 2.0],
                                        [1.0, np.nan, 2.0],
                                        [1.0, 2.0, 2.0]])
        self.plugin = FallingSnowLevel()

    def test_basic(self):
        """Test when all the points around the missing data are the same."""
        snow_level_data = np.ones((3, 3))
        snow_level_data[1, 1] = np.nan
        expected = np.array([[1.0, 1.0, 1.0],
                             [1.0, 1.0, 1.0],
                             [1.0, 1.0, 1.0]])
        snow_level_updated = self.plugin.fill_in_by_horizontal_interpolation(
            snow_level_data)
        self.assertArrayEqual(snow_level_updated, expected)

    def test_different_data(self):
        """Test when the points around the missing data have different
           values."""
        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, 1.5, 2.0],
                             [1.0, 2.0, 2.0]])
        snow_level_updated = self.plugin.fill_in_by_horizontal_interpolation(
            self.snow_level_data)
        self.assertArrayEqual(snow_level_updated, expected)

    def test_lots_missing(self):
        """Test when there's an extra missing value at the corner
           of the grid."""
        self.snow_level_data[2, 2] = np.nan
        expected = np.array([[1.0, 1.0, 2.0],
                             [1.0, 1.5, 2.0],
                             [1.0, 2.0, np.nan]])
        snow_level_updated = self.plugin.fill_in_by_horizontal_interpolation(
            self.snow_level_data)
        self.assertArrayEqual(snow_level_updated, expected)


class Test_process(IrisTest):

    """Test the FallingSnowLevel processing works"""

    def setUp(self):
        """Set up cubes."""

        temp_vals = [278.0, 280.0, 285.0, 286.0]
        pressure_vals = [93856.0, 95034.0, 96216.0, 97410.0]

        data = np.ones((2, 1, 3, 3))
        relh_data = np.ones((2, 1, 3, 3)) * 0.65

        temperature = set_up_cube(data, 'air_temperature', 'K',
                                  realizations=np.array([0, 1]))
        relative_humidity = set_up_cube(relh_data,
                                        'relative_humidity', '%',
                                        realizations=np.array([0, 1]))
        pressure = set_up_cube(data, 'air_pressure', 'Pa',
                               realizations=np.array([0, 1]))
        self.height_points = np.array([5., 195., 200.])
        self.temperature_cube = set_up_height_cube(
            self.height_points, cube=temperature)
        self.relative_humidity_cube = (
            set_up_height_cube(self.height_points, cube=relative_humidity))
        self.pressure_cube = set_up_height_cube(
            self.height_points, cube=pressure)
        for i in range(0, 3):
            self.temperature_cube.data[i, ::] = temp_vals[i+1]
            self.pressure_cube.data[i, ::] = pressure_vals[i+1]
            # Add hole in middle of data.
            self.temperature_cube.data[i, :, :, 1, 1] = temp_vals[i]
            self.pressure_cube.data[i, :, :, 1, 1] = pressure_vals[i]

        self.orog = iris.cube.Cube(np.ones((3, 3)),
                                   standard_name='surface_altitude', units='m')
        self.land_sea = iris.cube.Cube(np.ones((3, 3)),
                                       standard_name='land_binary_mask',
                                       units='m')
        self.orog.add_dim_coord(
            iris.coords.DimCoord(np.linspace(-45.0, 45.0, 3),
                                 'latitude', units='degrees'), 0)
        self.orog.add_dim_coord(iris.coords.DimCoord(np.linspace(120, 180, 3),
                                                     'longitude',
                                                     units='degrees'), 1)
        self.land_sea.add_dim_coord(
            iris.coords.DimCoord(np.linspace(-45.0, 45.0, 3),
                                 'latitude', units='degrees'), 0)
        self.land_sea.add_dim_coord(
            iris.coords.DimCoord(np.linspace(120, 180, 3),
                                 'longitude', units='degrees'), 1)

    def test_basic(self):
        """Test that process returns a cube with the right name and units."""
        result = FallingSnowLevel().process(
            self.temperature_cube, self.relative_humidity_cube,
            self.pressure_cube, self.orog, self.land_sea)
        expected = np.ones((2, 3, 3)) * 66.88732723
        self.assertIsInstance(result, iris.cube.Cube)
        self.assertEqual(result.name(), "falling_snow_level_asl")
        self.assertEqual(result.units, Unit('m'))
        self.assertArrayAlmostEqual(result.data, expected)

    def test_data(self):
        """Test that the falling snow level process returns a cube
        containing the expected data when points at sea-level."""
        expected = np.ones((2, 3, 3)) * 65.88732723
        expected[:, 1, 1] = 0.0
        orog = self.orog
        orog.data = orog.data * 0.0
        land_sea = self.land_sea
        land_sea = land_sea * 0.0
        result = FallingSnowLevel().process(
            self.temperature_cube, self.relative_humidity_cube,
            self.pressure_cube, orog, land_sea)
        self.assertIsInstance(result, iris.cube.Cube)
        self.assertArrayAlmostEqual(result.data, expected)


if __name__ == '__main__':
    unittest.main()
