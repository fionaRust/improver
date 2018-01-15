# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# (C) British Crown Copyright 2017 Met Office.
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
"""Module to contain statistical operations."""

import iris
import numpy as np
import warnings
from improver.utilities.cube_checker import find_percentile_coordinate


class ProbabilitiesFromPercentiles2D(object):
    """
    Generate a 2-dimensional field of probabilities by interpolating a
    percentiled cube of data to required points.

    Examples:

        Given a reference field of values against a percentile coordinate, an
        interpolation is performed using another field of values of the same
        type (e.g. height). This returns the percentile with which these
        heights would be associated in the reference field. This effectively
        uses the field of values as a 2-dimensional set of thresholds, and the
        percentiles looked up correspond to the probabilities of these
        thresholds being reached.

        Snow-fall level::

            Reference field: Percentiled snow fall level (m ASL)
            Other field: Orography (m ASL)

            300m ----------------- 30th Percentile snow fall level
            200m ----_------------ 20th Percentile snow fall level
            100m ---/-\----------- 10th Percentile snow fall level
            000m --/---\----------  0th Percentile snow fall level
            ______/     \_________ Orogaphy

        The orography heights are compared against the heights that
        correspond with percentile values to find the band in which they
        fall; this diagram hides the 2-dimensional variability of the snow
        fall level. The percentile values are then interpolated to the
        height of the point being considered. This constructs a
        2-dimensional field of probabilities that snow will be falling at
        each point in the orography field.
    """

    def __init__(self, percentiles_cube, output_name=None):
        """
        Initialise class.

        Args:
            percentiles_cube (iris.cube.Cube):
                The percentiled field from which probabilities will be obtained
                using the input cube. This cube should contain a percentiles
                dimension, with fields of values that correspond to these
                percentiles. The cube passed to the process method will contain
                values of the same diagnostic (e.g. height) as this reference
                cube.
            output_name (str):
                The name of the cube being created,
                e.g.'probability_of_snowfall'.

        """
        self.percentiles_cube = percentiles_cube
        if output_name is not None:
            self.output_name = output_name
        else:
            self.output_name = "probability_of_{}".format(
                percentiles_cube.name())

    def __repr__(self):
        """Represent the configured plugin instance as a string."""
        result = ('<ProbabilitiesFromPercentiles2D: percentiles_cube: {}, '
                  'output_name: {}'.format(self.percentiles_cube,
                                           self.output_name))
        return result

    def create_probability_cube(self, cube):
        """
        Create a 2-dimensional probability cube in which to store the
        calculated probabilities.

        Args:
            cube (iris.cube.Cube):
                Template for the output probability cube.
        Returns:
            probability_cube (iris.cube.Cube):
                A new 2-dimensional probability cube with suitable metadata.
        """
        cube_format = next(cube.slices([cube.coord(axis='y'),
                                        cube.coord(axis='x')]))
        probabilities = cube_format.copy(data=np.full(cube_format.shape,
                                                      np.nan, dtype=float))
        probabilities.units = 1
        probabilities.rename(self.output_name)
        return probabilities

    def percentile_interpolation(self, threshold_cube, percentiles_cube):
        """
        Perform the interpolation between 2-dimensional percentile fields to
        construct the probability field for a given set of thresholds.

        Args:
            threshold_cube (iris.cube.Cube):
                A 2-dimensional cube of "threshold" values for which it is
                desired to obtain probability values from the percentiled
                reference cube.
            percentiles_cube (iris.cube.Cube):
                A cube of 2-dimensional fields on several different percentile
                levels.
        Returns:
            probabilities (iris.cube.Cube):
                A 2-dimensional cube of probabilities obtained by interpolating
                between percentile values.
        """
        percentile_coordinate = find_percentile_coordinate(percentiles_cube)
        percentiles = percentile_coordinate.points
        pdata = np.full(threshold_cube.shape, np.nan, dtype=float)

        flagme = False
        iii = 0
        for x in range(threshold_cube.shape[1]):
            for y in range(threshold_cube.shape[0]):
                temp = percentiles_cube.data[:, y, x]
                if np.any(np.diff(temp) == 0):
                    flagme = True

                pdata[y, x] = np.interp(threshold_cube.data[y, x],
                                        percentiles_cube.data[:, y, x],
                                        percentiles, left=0, right=100)
                if flagme is True:
                    if pdata[y, x] > 0.:
                        print 'Percentiles', percentiles
                        print 'Percentile heights', percentiles_cube.data[:, y, x]
                        print 'Site Height', threshold_cube.data[y, x]
                        print 'Interpolated', pdata[y, x]
                        iii += 1
                    if pdata[y, x] > 0. and threshold_cube.data[y, x] == 0.:
                        pdata[y, x] = 0.
                    flagme = False

                if iii > 10:
                    raise Exception('Nope')

        print pdata.min()
        print pdata.mean()
        print pdata.max()
        probabilities = self.create_probability_cube(percentiles_cube)
        probabilities.data = 0.01*pdata
        return probabilities

    def process(self, threshold_cube):
        """
        Slice the percentiles cube over any non-spatial coordinates
        (realization, time, etc) if present, and call the percentile
        interpolation method for each resulting cube.

        Args:
            threshold_cube (iris.cube.Cube):
                A cube of values, that effectively behave as thresholds, for
                which it is desired to obtain probability values from a
                percentiled reference cube.
        Returns:
            output_cubes (iris.cube.Cube):
                A cube of probabilities obtained by interpolating between
                percentile values at the "threshold" level.
        """
        percentile_coordinate = find_percentile_coordinate(
            self.percentiles_cube)
        cube_slices = self.percentiles_cube.slices(
            [percentile_coordinate, self.percentiles_cube.coord(axis='y'),
             self.percentiles_cube.coord(axis='x')])

        if threshold_cube.ndim != 2:
            msg = ('threshold cube has too many ({} > 2) dimensions - slicing '
                   'to x-y grid'.format(threshold_cube.ndim))
            warnings.warn(msg)
            threshold_cube = next(threshold_cube.slices([
                threshold_cube.coord(axis='y'),
                threshold_cube.coord(axis='x')]))

        if threshold_cube.units != self.percentiles_cube.units:
            threshold_cube.convert_units(self.percentiles_cube.units)

        output_cubes = iris.cube.CubeList()
        for cube_slice in cube_slices:
            output_cube = self.percentile_interpolation(threshold_cube,
                                                        cube_slice)
            output_cubes.append(output_cube)
        if len(output_cubes) > 1:
            output_cubes = output_cubes.merge_cube()
        else:
            output_cubes = output_cubes[0]

        return output_cubes
