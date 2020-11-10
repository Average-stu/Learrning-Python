import argparse
import socket
import threading

def connection_scan(target_ip, target_port):
    try:
        conn_socket =socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn_socket.connect((target_ip,target_port))
        conn_socket.send(b'Banner_query\r\n')
        print("[+] {}/tcp open".format(target_port))
    except OSError:
        print("[-] {}/tcp closed".format(target_port))
    finally:
        conn_socket.close()

def port_scan(target,port_num):
    try:
        target_ip =socket.gethostbyname(target)
        print('[+] Scan Result For: {}'.format(target_ip))
        connection_scan(target_ip, int(port_num))
    except OSError:
        print('[^] Cannot resolve {}: Unknown host'.format(target))

    t = threading.Thread(target=connection_scan, args=(target, int(port_num)))
    t.start()


def argument_parser():
    parser =argparse.ArgumentParser(description="TCp port scanner. Accept a hostname/IP address and list of port to"
                                    "scan. attempt to identify the service running on a port.")
    parser.add_argument("-o", "--host", nargs="?", help="Host IP address")
    parser.add_argument("-p", "--ports", nargs="?", help="Comma-separted port list, such as '25,80,8080")

    vars_args =vars(parser.parse_args())

    return vars_args

if __name__ == "__main__":
    try:
        user_args = argument_parser()
        host = user_args["host"]
        port_list = user_args["ports"].split(",")
        for port in port_list:
            port_scan(host, port)
    except AttributeError:
        print("Error. Please Provide the command-line argument before running")