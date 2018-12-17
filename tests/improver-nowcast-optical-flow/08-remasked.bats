#!/usr/bin/env bats
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

. $IMPROVER_DIR/tests/lib/utils

@test "optical-flow remasked" {

  improver_check_skip_acceptance
  KGO1="nowcast-optical-flow/remasked/ucomp_kgo.nc"
  KGO2="nowcast-optical-flow/remasked/vcomp_kgo.nc"

  COMP1="201811271330_radar_rainrate_remasked_composite_2km_UK.nc"
  COMP2="201811271345_radar_rainrate_remasked_composite_2km_UK.nc"
  COMP3="201811271400_radar_rainrate_remasked_composite_2km_UK.nc"

  # Run processing with radar data whose masks differ
  run improver nowcast-optical-flow \
    "$IMPROVER_ACC_TEST_DIR/nowcast-optical-flow/remasked/$COMP1" \
    "$IMPROVER_ACC_TEST_DIR/nowcast-optical-flow/remasked/$COMP2" \
    "$IMPROVER_ACC_TEST_DIR/nowcast-optical-flow/remasked/$COMP3" \
    --output_dir "$TEST_DIR"
  [[ "$status" -eq 0 ]]

  UCOMP="20181127T1400Z-PT0000H00M-precipitation_advection_x_velocity.nc"
  VCOMP="20181127T1400Z-PT0000H00M-precipitation_advection_y_velocity.nc"

  improver_check_recreate_kgo "$UCOMP" $KGO1
  improver_check_recreate_kgo "$VCOMP" $KGO2

  # Run nccmp to compare the output and kgo.
  improver_compare_output "$TEST_DIR/$UCOMP" \
      "$IMPROVER_ACC_TEST_DIR/$KGO1"
  improver_compare_output "$TEST_DIR/$VCOMP" \
      "$IMPROVER_ACC_TEST_DIR/$KGO2"
}

