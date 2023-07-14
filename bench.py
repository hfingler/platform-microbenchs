import sys, os
import subprocess
import timeit, time
import re

#
# Helpers
#
def setup():
    run_shell_command("sudo yum install fio iperf wget")
    run_shell_command("sudo yum install -y openssl-devel hmaccalc zlib-devel binutils-devel elfutils-libelf-devel ncurses-devel make gcc bc bison flex")
     
def cleanup():
    run_shell_command("rm -r linux-4.19.288.tar.xz linux-4.19.288")
    run_shell_command("rm -f tmp_fio.cfg fio-output.log")

def run_shell_command(command):
    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
        return output.strip()
    except subprocess.CalledProcessError as e:
        # If the command fails, you can handle the exception here
        print(f"Error executing command: {e}")
        sys.exit(1)

#
# Network
#
def test_network(endpoint_ip):
    print(f"\nMake sure the machine at IP {endpoint_ip} is running the iperf server")
    print(f"or this will fail. This is done by executing: iperf -s\n")

    res = []
    #cmd = f"iperf -n 1024M -c {endpoint_ip}"
    for parallel in [1,8,32]:
        cmd = f"iperf -P {parallel} -t 10 -c {endpoint_ip}"
        out = run_shell_command(cmd)
        out = out.splitlines()[-1].split()
        tput = f"{out[-2]} {out[-1]}"
        print(f"{tput},")
        res.append(out[-2])
    print(",".join(res))

#
# Disk
# 
def get_bandwidth_fio_line(line):
    match = re.search("BW=(\S*)", line)
    if match is not None:
        return str(match.group(1))
    return None

def get_bandwidths_fio_output(filename):
    with open(filename) as f:
        lines = f.readlines()

    bws = {"randwrite" : None, "seqwrite": None, 
           "randread": None, "seqread" : None}

    for i in range(len(lines)-1):
        for k in bws.keys():
            if k in lines[i] and "groupid=" in lines[i]:
                print("found")
                bws[k] = get_bandwidth_fio_line(lines[i+1])
                break
    return bws

def replace_fio_cfg(path):
    with open("fio_template.cfg") as fin:
        with open("tmp_fio.cfg", "w") as fout:
            for line in fin:
                fout.write(line.replace('##filepath##', path))

def run_fio():
    run_shell_command("fio -o fio-output.log --max-jobs=8 tmp_fio.cfg")

def test_disk(file_path):
    replace_fio_cfg(file_path)
    #run_fio()
    bws = get_bandwidths_fio_output("fio-output.log")
    print(bws)
    run_shell_command("rm -f file_path")
#
# Kernel compilatiopn
#
def download_kernel():
    run_shell_command("wget https://cdn.kernel.org/pub/linux/kernel/v4.x/linux-4.19.288.tar.xz")
    run_shell_command("tar xf linux-4.19.288.tar.xz")

def compile_kernel():
    run_shell_command("cp kernel_config linux-4.19.288/.config")
    nprocs = run_shell_command("nproc")
    run_shell_command(f"cd linux-4.19.288 && make olddefconfig && make -j{nprocs}")
    
def test_compile(n_runs=1):
    total_time = timeit.timeit(lambda: compile_kernel(), number=int(n_runs))
    print(total_time)
    return total_time/int(n_runs)

#
# main
#
if __name__ == '__main__':
    if len(sys.argv) != 3 :
        print("Need one of the below options:")
        print(f"{sys.argv[0]} network <endpoint VM IP>")
        print(f"{sys.argv[0]} disk <directory (mounted on the device to test)>")
        print(f"{sys.argv[0]} compile <# of compile runs>")
    
    setup()

    if sys.argv[1] == 'network':
        test_network(sys.argv[2])
    elif sys.argv[1] == 'disk':
        test_disk(sys.argv[2])
    elif sys.argv[1] == 'compile':
        test_compile(sys.argv[2])
    else:
        print("Invalid arguments!")

    cleanup()