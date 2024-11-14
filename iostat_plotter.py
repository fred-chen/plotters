#! /usr/bin/env python3

import time
import os
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import sys
import getopt
import re
from datetime import datetime


def usage():
    print(
        "Usage: python3 iostat_plotter.py iostat_log_name [-s <start_time>] [-e <end_time>] [-d <device>] [-y] [-h]")
    print("Options:")
    print("  -s, --start_time <start_time>  Start time in format 'YYYY-MM-DD HH:MM:SS' or simply a sequence number")
    print("  -e, --end_time <end_time>      End time in format 'YYYY-MM-DD HH:MM:SS' or simply a sequence number")
    print("  -d, --dev <device>             Device name")
    print("  -y, --omit_first               Omit the first output of iostat")
    print("  -h, --help                     Display this help message")
    print("Example:")
    print("  python3 iostat_plotter.py iostat.log -s '2024-11-14 10:32:28' -e '2024-11-14 10:33:28' -d nvme2n1")


def load_data(log_file, omit_first=False):
    with open(log_file, 'r') as f:
        lines = [line for line in f.readlines() if line.strip()]

    """
    Sample of LNQA iostat log file format:
    Thu Nov 14 10:32:28 CST 2024
    Linux 4.19.91-26.an8.x86_64 (node5)     11/14/2024      _x86_64_        (64 CPU)

    Device            r/s     w/s     rMB/s     wMB/s   rrqm/s   wrqm/s  %rrqm  %wrqm r_await w_await aqu-sz rareq-sz wareq-sz  svctm  %util
    nvme2n1        388.34  639.40     16.35     28.67     0.00     0.00   0.00   0.00    0.16    0.06   0.09    43.10    45.92   0.06   6.06
    nvme3n1       1115.82 1458.52     47.73     65.65     0.00     0.00   0.00   0.00    2.34    0.45   3.77    43.80    46.09   0.05  13.25
    sde              0.00    0.00      0.00      0.00     0.00     0.00   0.00   0.00    0.00    0.00   0.00     0.00     0.00   0.00   0.00
    sda              0.00    0.00      0.00      0.00     0.00     0.00   0.00   0.00    0.00    0.00   0.00     0.00     0.00   0.00   0.00

    """
    reg_date_line = re.compile(r'^\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2} \w{3} \d{4}$')
    data_frame = pd.DataFrame()

    seq = 0
    column_names = None
    timestamp = None
    omit_factor = 0
    data_list = []
    for line in lines:
        # if there's time stamp, then it's LNQA format
        # search for date line and extract timestamp
        m = re.search(reg_date_line, line)
        if m:
            timestr = m.group().strip() if m else timestamp
            timestamp = datetime.strptime(timestr, "%a %b %d %H:%M:%S %Z %Y")
            omit_factor = 0
        elif line.startswith("Dev"):
            # header lines
            omit_factor += 1
            if not column_names:
                column_names = line.split()
            seq += 1
        elif column_names:
            # data lines
            data = line.split()
            if not column_names or len(data) != len(column_names) or (omit_first and omit_factor <= 1):
                # skip invalid data
                continue
            data_list.append([seq, timestamp]+data)
        if seq and seq % 10000 == 0:
            print(f"Processing line {seq}...")

    data_frame = pd.DataFrame(data_list, columns=['seq', 'time']+column_names)
    # print(data_frame)
    return data_frame


def filter_data(df, start_time=None, end_time=None, dev=None):
    # filter data
    try:
        start_time = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S") if start_time else None
    except ValueError:
        start_time = int(start_time) if start_time else None
    try:
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S") if end_time else None
    except ValueError:
        end_time = int(end_time) if end_time else None
    if isinstance(start_time, datetime):
        df = df[df['time'] >= start_time]
    else:
        df = df[df['seq'] >= start_time] if start_time else df
    if isinstance(end_time, datetime):
        df = df[df['time'] <= end_time]
    else:
        df = df[df['seq'] <= end_time] if end_time else df
    if dev:
        df = df[df['Device'].str.match(dev)]
    return df


def plot_awaits(df, start_time=None, end_time=None, dev=None):
    """Plot IO awaits

    Args:
        df (pd.DataFrame): Dataframe of iostat data
        start_time (datetime): Start time
        end_time (datetime): End time
        dev (str): Device name
    """
    if df.empty:
        print("No data to plot.")
        return

    if df.iloc[0].loc['time'] is None:
        df['time'] = df['seq']

    # plot
    plt.figure(figsize=(16, 8))
    for dev in df['Device'].unique():
        data = df[df['Device'] == dev]
        for label in 'r_await', 'w_await':
            plt.plot(data['time'], pd.to_numeric(data[label]), label=dev+" "+label)

    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=20))
    if isinstance(df.iloc[0].loc['time'], datetime):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y%m%d %H:%M:%S"))
    else:
        plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    # plt.locator_params(axis='x', nbins=20)
    plt.locator_params(axis='y', nbins=20)
    # plt.xlabel("Time (s)")
    plt.ylabel('Latency (ms)')
    plt.title(f"IO Awaits ({len(df)} samples)")
    plt.legend()
    plt.tight_layout()
    filename = f"iostat_awaits_{dev}"
    filename += f"_s{start_time}" if start_time else ""
    filename += f"_e{end_time}.png" if end_time else ".png"
    plt.savefig(filename)
    plt.close()
    print(f"{filename} 已保存。")


def plot_reqsz(df, start_time=None, end_time=None, dev=None):
    if df.empty:
        print("No data to plot.")
        return

    if df.iloc[0].loc['time'] is None:
        df['time'] = df['seq']

    # plot
    plt.figure(figsize=(16, 8))
    for dev in df['Device'].unique():
        data = df[df['Device'] == dev]
        for label in 'rareq-sz', 'wareq-sz':
            plt.plot(data['time'], pd.to_numeric(data[label]), label=dev+" "+label)

    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=20))
    if isinstance(df.iloc[0].loc['time'], datetime):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y%m%d %H:%M:%S"))
    else:
        plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    # plt.locator_params(axis='x', nbins=20)
    plt.locator_params(axis='y', nbins=20)
    # plt.xlabel("Time (s)")
    plt.ylabel('Request Size (KB)')
    plt.title(f"Average Request Size ({len(df)} samples)")
    plt.legend()
    plt.tight_layout()
    filename = f"iostat_reqsz_{dev}"
    filename += f"_s{start_time}" if start_time else ""
    filename += f"_e{end_time}.png" if end_time else ".png"
    plt.savefig(filename)
    plt.close()
    print(f"{filename} 已保存。")


def plot_aqusz(df, start_time=None, end_time=None, dev=None):
    if df.empty:
        print("No data to plot.")
        return

    if df.iloc[0].loc['time'] is None:
        df['time'] = df['seq']

    # plot
    plt.figure(figsize=(16, 8))
    for dev in df['Device'].unique():
        data = df[df['Device'] == dev]
        for label in ['aqu-sz']:
            plt.plot(data['time'], pd.to_numeric(data[label]), label=dev+" "+label)

    plt.xticks(rotation=45)
    plt.gca().xaxis.set_major_locator(ticker.MaxNLocator(nbins=20))
    if isinstance(df.iloc[0].loc['time'], datetime):
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%Y%m%d %H:%M:%S"))
    else:
        plt.gca().xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: f"{int(x)}"))
    # plt.locator_params(axis='x', nbins=20)
    plt.locator_params(axis='y', nbins=20)
    # plt.xlabel("Time (s)")
    plt.ylabel('Queue Length')
    plt.title(f"Average Queue Length ({len(df)} samples)")
    plt.legend()
    plt.tight_layout()
    filename = f"iostat_aqusz_{dev}"
    filename += f"_s{start_time}" if start_time else ""
    filename += f"_e{end_time}.png" if end_time else ".png"
    plt.savefig(filename)
    plt.close()
    print(f"{filename} 已保存。")


def main(log_file, start_time=None, end_time=None, dev=None, omit_first=False):
    df = load_data(log_file, omit_first)
    df = filter_data(df, start_time, end_time, dev)
    plot_awaits(df, start_time, end_time, dev)
    plot_reqsz(df, start_time, end_time, dev)
    plot_aqusz(df, start_time, end_time, dev)


if __name__ == "__main__":
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "s:e:d:yh", [
                                       "start_time=", "end_time=", "dev=", "omit_first", "help"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    start_time, end_time, dev, omit_first = None, None, None, False

    for opt, arg in opts:
        if opt in ("-s", "--start_time"):
            start_time = arg
        elif opt in ("-e", "--end_time"):
            end_time = arg
        elif opt in ("-d", "--dev"):
            dev = arg
        elif opt in ("-y", "--omit_first"):
            omit_first = True
        elif opt in ("-h", "--help"):
            usage()
            sys.exit()
    for arg in args:
        log_file = arg

    if not os.path.exists(log_file):
        print(f"File {log_file} does not exist.")
        sys.exit(2)

    main(log_file, start_time, end_time, dev, omit_first)
