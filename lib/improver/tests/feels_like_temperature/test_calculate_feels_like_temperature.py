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
"""Unit tests for the feels_like_temperature.FeelsLikeTemperature plugin."""

import unittest
import numpy as np
from iris.tests import IrisTest

from improver.feels_like_temperature import calculate_feels_like_temperature
from improver.tests.ensemble_calibration.ensemble_calibration. \
    helper_functions import (set_up_temperature_cube, set_up_wind_speed_cube,
                             set_up_cube)


class Test_calculate_feels_like_temperature(IrisTest):
    """Test the feels like temperature function."""

    def setUp(self):
        """Create cubes to input."""

        self.temperature_cube = set_up_temperature_cube()
        self.wind_speed_cube = set_up_wind_speed_cube()

        # create cube with metadata and values suitable for pressure.
        pressure_data = (
            np.tile(np.linspace(100000, 110000, 9), 3).reshape(3, 1, 3, 3))
        pressure_data[0] -= 2
        pressure_data[1] += 2
        pressure_data[2] += 4
        self.pressure_cube = set_up_cube(
            pressure_data, "air_pressure", "Pa")

        # create cube with metadata and values suitable for relative humidity.
        relative_humidity_data = (
            np.tile(np.linspace(0, 0.6, 9), 3).reshape(3, 1, 3, 3))
        relative_humidity_data[0] += 0
        relative_humidity_data[1] += 0.2
        relative_humidity_data[2] += 0.4
        self.relative_humidity_cube = set_up_cube(
            relative_humidity_data, "relative_humidity", "1")

    def test_temperature_less_than_10(self):
        """Test values of feels like temperature when temperature < 10
        degrees C."""

        self.temperature_cube.data = np.full((3, 1, 3, 3), 282.15)
        expected_result = (
            [[291.86349999999999, 278.64456962610683, 277.09415911417699]])
        result = calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube,
            self.relative_humidity_cube, self.pressure_cube)
        self.assertArrayAlmostEqual(result[0, :, 0].data, expected_result)

    def test_temperature_between_10_and_20(self):
        """Test values of feels like temperature when temperature is between 10
        and 20 degress C."""

        self.temperature_cube.data = np.full((3, 1, 3, 3), 287.15)
        expected_result = (
            [[290.98659999999995, 283.21703936566627, 280.66949456155015]])
        result = calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube,
            self.relative_humidity_cube, self.pressure_cube)
        self.assertArrayAlmostEqual(result[0, :, 0].data, expected_result)

    def test_temperature_greater_than_20(self):
        """Test values of feels like temperature when temperature > 20
        degrees C."""

        self.temperature_cube.data = np.full((3, 1, 3, 3), 294.15)
        expected_result = (
            [[292.28999999999996, 287.78967281999996, 283.28939005999996]])
        result = calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube,
            self.relative_humidity_cube, self.pressure_cube)
        self.assertArrayAlmostEqual(result[0, :, 0].data, expected_result)

    def test_temperature_range_and_bounds(self):
        """Test temperature values across the full range including boundary
        temperatures 10 degrees Celcius and 20 degrees Celcius"""

        self.temperature_cube = set_up_temperature_cube()[0]
        data = np.linspace(-10, 30, 9).reshape(1, 3, 3)
        data = data + 273.15
        self.temperature_cube.data = data
        expected_result = np.array(
            [[[280.05499999999995, 260.53790629143003, 264.74498482704507],
              [270.41447781935329, 276.82207516713441, 273.33273779977668],
              [264.11408954000001, 265.66779343999997, 267.76949669999999]]])
        result = calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube[0],
            self.relative_humidity_cube[0], self.pressure_cube[0])
        self.assertArrayAlmostEqual(result.data, expected_result)

    def test_name_and_units(self):
        """Test correct outputs for name and units."""

        expected_name = "feels_like_temperature"
        expected_units = 'K'
        result = calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube,
            self.relative_humidity_cube, self.pressure_cube)
        self.assertEqual(result.name(), expected_name)
        self.assertEqual(result.units, expected_units)

    def test_different_units(self):
        """Test that values are correct from input cubes with
        different units"""

        self.temperature_cube.convert_units('fahrenheit')
        self.wind_speed_cube.convert_units('knots')
        self.relative_humidity_cube.convert_units('%')
        self.pressure_cube.convert_units('hPa')

        data = np.array(
            [[[257.05949999999996, 220.76791360990785, 231.12778815651939],
              [244.45492051555226, 259.30003784711084, 275.1347693144458],
              [264.70048734, 274.29471727999999, 286.60422231999996]]])
        # convert to fahrenheit
        expected_result = data * (9.0/5.0) - 459.67
        result = calculate_feels_like_temperature(
            self.temperature_cube[0], self.wind_speed_cube[0],
            self.relative_humidity_cube[0], self.pressure_cube[0])
        self.assertArrayAlmostEqual(result.data, expected_result)

    def test_unit_conversion(self):
        """Test that input cubes have the same units at the end of the function
        as they do at input"""

        self.temperature_cube.convert_units('fahrenheit')
        self.wind_speed_cube.convert_units('knots')
        self.relative_humidity_cube.convert_units('%')
        self.pressure_cube.convert_units('hPa')

        calculate_feels_like_temperature(
            self.temperature_cube, self.wind_speed_cube,
            self.relative_humidity_cube, self.pressure_cube)

        temp_units = self.temperature_cube.units
        wind_speed_units = self.wind_speed_cube.units
        relative_humidity_units = self.relative_humidity_cube.units
        pressure_units = self.pressure_cube.units

        self.assertEqual(temp_units, 'fahrenheit')
        self.assertEqual(wind_speed_units, 'knots')
        self.assertEqual(relative_humidity_units, '%')
        self.assertEqual(pressure_units, 'hPa')


if __name__ == '__main__':
    unittest.main()
