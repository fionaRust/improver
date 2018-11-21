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
"""Unit tests for psychrometric_calculations WetBulbTemperature"""

import unittest
import iris
from iris.cube import Cube
from iris.tests import IrisTest
from iris.coords import DimCoord
from cf_units import Unit
import numpy as np

from improver.psychrometric_calculations.psychrometric_calculations import (
    TemperatureToPotentialTemperature)
from improver.utilities.warnings_handler import ManageWarnings


class Test__repr__(IrisTest):

    """Test the repr method."""

    def test_basic(self):
        """Test that the __repr__ returns the expected string."""
        result = str(TemperatureToPotentialTemperature())
        msg = ("<TemperatureToPotentialTemperature: reference_pressure: "
               "1000.0, reference_pressure_units: hPa>")
        self.assertEqual(result, msg)


class Test_process(IrisTest):

    """Test the calculation of Potential Temperature in the process method."""

    def setUp(self):
        """Set up cubes required for unit tests."""
        longitude = DimCoord([0, 10, 20], 'longitude', units='degrees')
        time = DimCoord([1491955200], 'time')
        self.temperature = Cube([283.15, 283.15, 283.15], 'air_temperature',
                                units='K',
                                dim_coords_and_dims=[(longitude, 0)])
        self.temperature.add_aux_coord(time)
        self.pressure = Cube([1.E5, 9.9E4, 1.1E5], 'air_pressure', units='Pa',
                             dim_coords_and_dims=[(longitude, 0)])
        self.pressure.add_aux_coord(time)

    def test_cube_metadata(self):
        """Check metadata of returned cube."""

        result = TemperatureToPotentialTemperature().process(
            self.temperature, self.pressure)

        self.assertIsInstance(result, Cube)
        self.assertEqual(result.units, Unit('K'))
        self.assertEqual(result.name(), 'air_potential_temperature')

    def test_cube_data(self):
        """Check data of returned cube."""

        result = TemperatureToPotentialTemperature().process(
            self.temperature, self.pressure)
        expected_data = np.array([283.15, 283.963835, 275.547178])
        self.assertArrayAlmostEqual(result.data, expected_data)

    def test_different_units(self):
        """Check we still get the same result if the input
           is in different units"""
        self.pressure.convert_units("hPa")
        result = TemperatureToPotentialTemperature().process(
            self.temperature, self.pressure)
        expected_data = np.array([283.15, 283.963835, 275.547178])
        self.assertArrayAlmostEqual(result.data, expected_data)
        self.assertEqual(result.units, Unit('K'))

    def test_different_temperature_units(self):
        """Check we still get the same result if the input is in
           different units"""
        self.temperature.convert_units("celsius")
        print(self.temperature)
        result = TemperatureToPotentialTemperature().process(
             self.temperature, self.pressure)
        expected_data = np.array([10., 10.813835, 2.397178])
        self.assertArrayAlmostEqual(result.data, expected_data)
        self.assertEqual(result.units, Unit('celsius'))


if __name__ == '__main__':
    unittest.main()
