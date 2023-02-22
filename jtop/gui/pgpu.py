# -*- coding: UTF-8 -*-
# This file is part of the jetson_stats package (https://github.com/rbonghi/jetson_stats or http://rnext.it).
# Copyright (c) 2019-2023 Raffaello Bonghi.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import curses
from .jtopgui import Page
# Graphics elements
from .lib.common import NColors
from .lib.common import plot_name_info
from .lib.chart import Chart
from .lib.process_table import ProcessTable
from .lib.common import unit_to_string
from .lib.linear_gauge import basic_gauge, freq_gauge


def gpu_gauge(stdscr, pos_y, pos_x, size, gpu_data, idx):
    gpu_status = gpu_data['status']
    # Data gauge
    data = {
        'name': 'GPU' if idx == 0 else 'GPU{idx}'.format(idx=idx),
        'color': NColors.green() | curses.A_BOLD,
        'values': [(gpu_status['load'], NColors.igreen())],
    }
    if 'freq' in gpu_data:
        # Draw current frequency
        curr_string = unit_to_string(gpu_data['freq']['cur'], gpu_data['freq']['unit'], 'Hz')
        stdscr.addstr(pos_y, pos_x + size - 8, curr_string, NColors.italic())
    # Draw gauge
    basic_gauge(stdscr, pos_y, pos_x, size - 10, data, bar=" ")


def compact_gpu(stdscr, pos_y, pos_x, width, jetson):
    line_counter = 0
    # Status all GPUs
    if jetson.gpu:
        for idx, gpu in enumerate(jetson.gpu):
            gpu_gauge(stdscr, pos_y + line_counter, pos_x, width, gpu, idx)
            line_counter += 1
    else:
        data = {
            'name': 'GPU',
            'color': NColors.green() | curses.A_BOLD,
            'online': False,
            'coffline': NColors.igreen(),
            'message': 'NOT AVAILABLE',
        }
        basic_gauge(stdscr, pos_y, pos_x, width - 2, data)
        line_counter = 1
    return line_counter


class GPU(Page):

    def __init__(self, stdscr, jetson):
        super(GPU, self).__init__("GPU", stdscr, jetson)
        # Initialize GPU chart
        self.chart_gpus = []
        for idx, name in enumerate(self.jetson.gpu):
            chart = Chart(jetson, "GPU{name}".format(name=idx + 1), self.update_chart, color_text=curses.COLOR_GREEN)
            self.chart_gpus += [chart]
        # Add Process table
        self.process_table = ProcessTable(self.stdscr, self.jetson.processes)

    def update_chart(self, jetson, name):
        # Decode GPU name
        idx = int(name[3:]) - 1
        gpu_data = jetson.gpu[idx]
        gpu_status = gpu_data['status']
        # Append in list
        return {
            'value': [gpu_status['load']],
        }

    def draw(self, key, mouse):
        # Screen size
        height, width, first = self.size_page()
        # Measure height
        gpu_height = (height * 2 // 3 - 3) // len(self.jetson.gpu)
        # Plot all GPU temperatures
        self.stdscr.addstr(first + 1, 1, "Temperatures:", curses.A_NORMAL)
        for idx, temp in enumerate(self.jetson.temperature):
            if 'GPU' in temp:
                value = self.jetson.temperature[temp]['temp']
                self.stdscr.addstr(first + 1, 15, temp + " ", curses.A_BOLD)
                self.stdscr.addstr(str(value) + "C", curses.A_NORMAL)
        # Draw all GPU
        for idx, (chart, gpu_data) in enumerate(zip(self.chart_gpus, self.jetson.gpu)):
            gpu_status = gpu_data['status']
            gpu_freq = gpu_data['freq']
            # Set size chart gpu
            size_x = [1, width - 2]
            size_y = [first + 2 + idx * (gpu_height + 1), first + 2 + (idx + 1) * (gpu_height - 3)]
            # Print status CPU
            governor = gpu_freq.get('governor', '')
            label_chart_gpu = "{percent: >3.0f}% - gov: {governor} - name: {name}".format(percent=gpu_status['load'], governor=governor, name=gpu_data['name'])
            # Draw GPU chart
            chart.draw(self.stdscr, size_x, size_y, label=label_chart_gpu)
            # Print all status GPU
            button_position = width // 4
            button_idx = 0
            # railgate status
            railgate_string = "Active" if gpu_status['railgate'] else "Disable"
            railgate_status = NColors.green() if gpu_status['railgate'] else NColors.red()
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1, "Railgate", railgate_string, color=railgate_status)
            button_idx += button_position
            # 3D scaling
            scaling_string = "Active" if gpu_status['3d_scaling'] else "Disable"
            scaling_status = NColors.green() if gpu_status['3d_scaling'] else NColors.red()
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "3D scaling", scaling_string, color=scaling_status)
            button_idx += button_position
            # Power control
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "Power ctrl", gpu_data['power_control'])
            button_idx += button_position
            # TPC PG Mask
            tpc_pg_mask_string = "ON" if gpu_status['tpc_pg_mask'] else "OFF"
            # tpc_pg_mask_status = NColors.green() if gpu_status['tpc_pg_mask'] else NColors.red()
            plot_name_info(self.stdscr, first + 1 + (idx + 1) * gpu_height - 1, 1 + button_idx, "TPC PG", tpc_pg_mask_string)
            button_idx += button_position
            # Checj if GPC data is included
            frq_size = width - 3
            if 'GPC' in gpu_freq:
                size_gpc_gauge = (width - 2) // (2 + len(gpu_freq['GPC']))
                for gpc_idx, gpc in enumerate(gpu_freq['GPC']):
                    freq_data = {
                        'name': 'GPC{idx}'.format(idx=gpc_idx),
                        'cur': gpc,
                        'unit': gpu_data['freq']['unit'],
                        'online': gpc > 0,
                    }
                    freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height, width // 2 + gpc_idx * (size_gpc_gauge) + 2, size_gpc_gauge - 1, freq_data)
                # Change size frequency GPU
                frq_size = width // 2
            # Print frequency info
            gpu_freq['name'] = "Frq"
            freq_gauge(self.stdscr, first + 1 + (idx + 1) * gpu_height, 1, frq_size, gpu_freq)
        # Draw all Processes
        height_table = height - first + 2 + gpu_height
        self.process_table.draw(first + 2 + gpu_height, 0, width, height_table, key, mouse)
# EOF
