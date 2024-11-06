#! /usr/bin/env python3

import os
import subprocess
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import sys


def main():
    if len(sys.argv) < 2:
        print('Usage: {} <iostat_output_filename> <device_name>'.format(sys.argv[0]))
        sys.exit(1)
    filename = sys.argv[1]
    devname  = sys.argv[2]
    csv = load(filename, devname)
    plot(csv, f"{devname} in {os.path.basename(filename)}", devname)


def load(filename: str, devname: str = "") -> pd.DataFrame:
    parepared_filepath = prepare_data(filename, devname)
    print(f'Prepared file: {parepared_filepath}')
    csv = pd.read_csv(parepared_filepath, sep=r'\s+', engine='python')
    csv.insert(0, 'Seq.', range(1, len(csv) + 1))
    print(csv[:5])
    # csv['Time'] = pd.to_datetime(csv['Time'])
    return csv


def plot(csv : pd.DataFrame, pngname: str = 'iostat.png', devname: str = ''):
    fig, ax = plt.subplots()
    fig.set_figheight(8)
    fig.set_figwidth(16)

    #csv[csv['Device'].str.contains(devname)].plot.line(ax=ax, x='Seq.', y='r_await', label='r_await')
    #csv[csv['Device'].str.contains(devname)].plot.line(ax=ax, x='Seq.', y='w_await', label='w_await')
    csv_filtered = csv[csv['Device'].str.contains(devname)]
    for device in csv_filtered['Device'].unique():
        device_data = csv_filtered[csv_filtered['Device'] == device]
        device_data.plot.line(ax=ax, x='Seq.', y='r_await', label=f'{device} r_await')
        device_data.plot.line(ax=ax, x='Seq.', y='w_await', label=f'{device} w_await')

    # ax.plot(subset['Time'], subset['r_await'], label='r_await')
    # ax.plot(subset['Time'], subset['w_await'], label='w_await')
    # ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
    # ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
    # ax.xaxis.set_major_locator(mdates.MinuteLocator())
    # ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
    # ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M:%S'))
    # plt.gcf().autofmt_xdate(rotation=90)

    # ax.xaxis.set_tick_params(rotation=60)
    ax.legend()
    plt.title(pngname)
    plt.tight_layout()

    plt.savefig(f"{pngname}.png")
    print("Saved to", f"{pngname}.png")
    plt.show()


def prepare_data(filename: str, devname: str) -> str:
    prepared_filepath = f'{filename}.parsed.csv'
    print(f'grep Device {filename} | head -1 > {prepared_filepath}')
    with open(prepared_filepath, 'w') as f:
        subprocess.run(f'grep Device {filename} | head -1', shell=True, stdout=f, check=True)
        if devname:
            subprocess.run(['grep', '-E', f"{devname}", filename], stdout=f, check=True)
        else:
            subprocess.run(['cat', filename], stdout=f, check=True)
    return prepared_filepath
    # csv = pd.read_csv(filename, delimiter=',')
    # csv['Time'] = pd.to_datetime(csv['Time'])
    # return csv

if __name__ == '__main__':
    main()