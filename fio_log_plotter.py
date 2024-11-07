import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import getopt


def parse_log(file_path, columns, log_type):
    try:
        df = pd.read_csv(file_path, sep=',', names=columns, usecols=[0, 1, 2], engine='python')
        df['time'] /= 1000  # 将毫秒转换为秒，方便绘图
        if log_type == 'bw':
            df['value'] /= 2**10  # 将KiB转换为MiB
        elif log_type == 'lat' or log_type == 'slat' or log_type == 'clat':
            df['value'] /= 10**9  # 将纳秒转换为秒
        else:
            pass
        return df
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到。")
        return None


def plot_log(df, title, y_label, star_time, end_time, file_name):
    """绘制日志数据图"""
    plt.figure(figsize=(16, 8))
    for direction, label in zip([0, 1, 2], ['Read', 'Write', 'Discard']):
        data = df[df['direction'] == direction]
        data_filtered = data[data['time'].between(
            star_time if start_time else data['time'].min(), end_time if end_time else data['time'].max())]
        if not data_filtered.empty:
            plt.plot(data_filtered['time'], data_filtered['value'], label=label)

    plt.xticks(rotation=45)
    plt.locator_params(axis='x', nbins=20)
    plt.ticklabel_format(style='plain', axis='y')
    plt.xlabel("Time (s)")
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()
    plt.tight_layout()
    plt.savefig(file_name)
    plt.close()
    print(f"{file_name} 已保存。")


def main(prefix, start_time=None, end_time=None):
    print(start_time, end_time)
    # 定义文件名和列格式
    log_files = {
        'bw': ('{}_bw.log'.format(prefix), ['time', 'value', 'direction']),
        'iops': ('{}_iops.log'.format(prefix), ['time', 'value', 'direction']),
        'lat': ('{}_lat.log'.format(prefix), ['time', 'value', 'direction']),
        'slat': ('{}_slat.log'.format(prefix), ['time', 'value', 'direction']),
        'clat': ('{}_clat.log'.format(prefix), ['time', 'value', 'direction']),
    }

    # 解析和绘图
    for log_type, (file_path, columns) in log_files.items():
        df = parse_log(file_path, columns, log_type)
        if df is not None:
            y_label = 'Bandwidth (MiB/s)' if log_type == 'bw' else ('IOPS' if log_type ==
                                                                    'iops' else 'Latency (s)')
            title = f"{log_type.upper()} Over Time"
            if start_time or end_time:
                plot_log(df, title, y_label, start_time, end_time,
                         f"{os.path.basename(prefix)}_s{start_time}_e{end_time}_{log_type}.png")
            else:
                plot_log(df, title, y_label, start_time, end_time,
                         f"{os.path.basename(prefix)}_{log_type}.png")


def usage():
    print(
        "usage: python {} [-s <start_time_sec> -e <end_time_sec>] <log_file_prefix>".format(sys.argv[0]))


if __name__ == "__main__":
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "s:e:h", ["start_time=", "end_time=", "help"])
    except getopt.GetoptError as err:
        print(err)
        usage()
        sys.exit(2)

    start_time = None
    end_time = None

    for opt, arg in opts:
        if opt in ("-s", "--start_time"):
            start_time = int(arg)
        elif opt in ("-e", "--end_time"):
            end_time = int(arg)
        elif opt in ("-h", "--help"):
            usage()
            sys.exit()
    prefix = args[0]

    main(prefix, start_time, end_time)
