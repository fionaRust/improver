# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017-2019 Met Office.
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
""" Unit tests for the nowcasting.AdvectField plugin """

import unittest
import numpy as np

from iris.tests import IrisTest

from improver.nowcasting.forecasting import (
    AdvectField, CreateExtrapolationForecast)
from improver.tests.set_up_test_cubes import set_up_variable_cube
from improver.tests.nowcasting.forecasting.test_AdvectField import (
    set_up_xy_velocity_cube)


def setup_orographic_enhancement_cube():
    """Set up an orogrpahic enhancement cube using central utilities"""
    data = np.array([[1, 1, 1],
                     [0, 1, 0],
                     [0, 0, 0],
                     [0, 0, 0]], dtype=np.float32)
    orographic_enhancement_cube = set_up_variable_cube(
        data, name="orographic_enhancement", units="mm/hr",
        spatial_grid="equalarea")
    return orographic_enhancement_cube


def setup_precipitation_cube():
    """Set up an precipitation cube using central utilities"""
    data = np.array([[1, 2, 1],
                     [1, 1, 1],
                     [0, 2, 0],
                     [1, 2, 1]], dtype=np.float32)
    precipitation_cube = set_up_variable_cube(
        data, name="lwe_precipitation_rate", units="mm/hr",
        spatial_grid="equalarea")
    return precipitation_cube


class SetUpCubes(IrisTest):
    def setUp(self):
        """Set up cubes needed for the __init__ method """
        self.precip_cube = setup_precipitation_cube()
        self.oe_cube = setup_orographic_enhancement_cube()
        self.vel_x = set_up_xy_velocity_cube("advection_velocity_x")
        self.vel_y = set_up_xy_velocity_cube("advection_velocity_y")
        for cube in [self.precip_cube, self.oe_cube]:
            cube.coord("projection_x_coordinate").points = 600*np.arange(3)
            cube.coord("projection_y_coordinate").points = 600*np.arange(4)


class Test__init__(SetUpCubes):
    """Test class initialisation"""

    def test_basic(self):
        """Test for simple case where __init__ does not change the input."""
        # Change the input cube so no orographic enhancement is expected.
        input_cube = self.precip_cube.copy()
        input_cube.rename("air_temperature")
        input_cube.units = "K"
        plugin = CreateExtrapolationForecast(
            input_cube.copy(), self.vel_x, self.vel_y)
        self.assertEqual(input_cube, plugin.input_cube)
        self.assertEqual(plugin.orographic_enhancement_cube, None)
        self.assertIsInstance(plugin.advection_plugin, AdvectField)

    def test_basic_with_metadata_dict(self):
        """Test for simple case where __init__ does not change the input and
           we use a metadata_dict."""
        # Change the input cube so no orographic enhancement is expected.
        input_cube = self.precip_cube.copy()
        input_cube.rename("air_temperature")
        input_cube.units = "K"
        # set up a metadata_dict
        metadata_dict = {"attributes": {"source": "IMPROVER"}}
        plugin = CreateExtrapolationForecast(
            input_cube.copy(), self.vel_x, self.vel_y,
            metadata_dict=metadata_dict)
        self.assertEqual(input_cube, plugin.input_cube)
        self.assertEqual(plugin.orographic_enhancement_cube, None)
        self.assertIsInstance(plugin.advection_plugin, AdvectField)
        self.assertEqual(plugin.advection_plugin.metadata_dict, metadata_dict)

    def test_no_orographic_enhancement(self):
        """Test what happens if no orographic enhancement cube is provided"""
        message = ("For precipitation fields, orographic enhancement cube "
                   "must be supplied.")
        with self.assertRaisesRegex(ValueError, message):
            CreateExtrapolationForecast(
                self.precip_cube, self.vel_x, self.vel_y)

    def test_orographic_enhancement(self):
        """Test what happens if an orographic enhancement cube is provided"""
        plugin = CreateExtrapolationForecast(
                self.precip_cube, self.vel_x, self.vel_y,
                orographic_enhancement_cube=self.oe_cube.copy())
        expected_data = np.array([[0.03125, 1.0, 0.03125],
                                  [1.0, 0.03125, 1.0],
                                  [0.0, 2.0, 0.0],
                                  [1.0, 2.0, 1.0]], dtype=np.float32)

        self.assertEqual(self.precip_cube.metadata, plugin.input_cube.metadata)
        self.assertArrayAlmostEqual(plugin.input_cube.data, expected_data)
        self.assertEqual(plugin.orographic_enhancement_cube, self.oe_cube)
        self.assertIsInstance(plugin.advection_plugin, AdvectField)


class Test__repr__(SetUpCubes):
    """Test class representation"""

    def test_basic(self):
        """Test string representation"""
        plugin = CreateExtrapolationForecast(
                self.precip_cube, self.vel_x, self.vel_y,
                orographic_enhancement_cube=self.oe_cube)
        result = str(plugin)
        expected_result = (
            '<CreateExtrapolationForecast: input_cube = '
            'lwe_precipitation_rate, orographic_enhancement_cube = '
            'orographic_enhancement, advection_plugin = <AdvectField: '
            'vel_x=advection_velocity_x, vel_y=advection_velocity_y, '
            'metadata_dict={}>>'
            )
        self.assertEqual(result, expected_result)


class Test_extrapolate(SetUpCubes):
    """Test the extrapolate method."""

    def test_without_orographic_enhancement(self):
        """Test plugin returns the correct advected forecast cube.
        In this case we have 600m grid spacing in our cubes, and 1m/s
        advection velocities in the x and y direction, so after 10 hours,
        our precipitation will have moved exactly one grid square along"""
        input_cube = self.precip_cube.copy()
        input_cube.rename("air_temperature")
        input_cube.units = "K"
        plugin = CreateExtrapolationForecast(
                input_cube, self.vel_x, self.vel_y)
        result = plugin.extrapolate(leadtime_minutes=10)
        expected_result = np.array([[np.nan, np.nan, np.nan],
                                    [np.nan, 1, 2],
                                    [np.nan, 1, 1],
                                    [np.nan, 0, 2]], dtype=np.float32)
        expected_result = np.ma.masked_invalid(expected_result)
        expected_forecast_period = np.array([600], dtype=np.int64)
        # Check we get the expected result, and the correct time coordinates.
        self.assertArrayEqual(expected_result.mask, result.data.mask)
        self.assertArrayAlmostEqual(expected_result.data, result.data.data)
        self.assertArrayAlmostEqual(
            result.coord("forecast_period").points, expected_forecast_period)
        self.assertEqual(result.coord("forecast_period").units, "seconds")
        self.assertEqual(result.coord("forecast_reference_time").points,
                         input_cube.coord("forecast_reference_time").points)
        self.assertEqual(result.coord("time").points,
                         input_cube.coord("time").points+600)

    def test_with_orographic_enhancement(self):
        """Test plugin returns the correct advected forecast cube, with
        orographic enhancement.
        In this case we have 600m grid spacing in our cubes, and 1m/s
        advection velocities in the x and y direction, so after 10 hours,
        our precipitation will have moved exactly one grid square along.
        The orographic enhancement has been removed before advecting, then
        added back on afterwards, leading to a different end result."""
        plugin = CreateExtrapolationForecast(
                self.precip_cube, self.vel_x, self.vel_y,
                orographic_enhancement_cube=self.oe_cube)
        result = plugin.extrapolate(leadtime_minutes=10)
        expected_result = np.array([[np.nan, np.nan, np.nan],
                                    [np.nan, 1.03125, 1.0],
                                    [np.nan, 1.0, 0.03125],
                                    [np.nan, 0, 2.0]], dtype=np.float32)
        expected_result = np.ma.masked_invalid(expected_result)
        expected_forecast_period = np.array([600], dtype=np.int64)
        # Check we get the expected result, and the correct time coordinates.
        self.assertArrayEqual(expected_result.mask, result.data.mask)
        self.assertArrayAlmostEqual(expected_result.data, result.data.data)
        self.assertArrayAlmostEqual(
            result.coord("forecast_period").points, expected_forecast_period)
        self.assertEqual(result.coord("forecast_period").units, "seconds")
        self.assertEqual(
            result.coord("forecast_reference_time").points,
            self.precip_cube.coord("forecast_reference_time").points)
        self.assertEqual(result.coord("time").points,
                         self.precip_cube.coord("time").points+600)

    def test_raises_error(self):
        """Test an error is raised if no leadtime is provided"""
        plugin = CreateExtrapolationForecast(
                self.precip_cube, self.vel_x, self.vel_y,
                orographic_enhancement_cube=self.oe_cube)
        message = ("leadtime_minutes must be provided in order to "
                   "produce an extrapolated forecast")
        with self.assertRaisesRegex(ValueError, message):
            plugin.extrapolate()


if __name__ == '__main__':
    unittest.main()
