#!/usr/bin/env python

"""
This script automates the build process of the timestamp program as well as
generates three plots based on padding message size, loss rate, and RTT.
To avoid potential incompatibility with different shells (bash ksh tcsh, etc),
python is used rather than usual shell scripts.
Also, this script is not as well written as the timestamp program, which is
largely due to the fact that the author has very limited experience with
python.
"""

from __future__ import print_function

import argparse
import getpass
import matplotlib.pyplot as plt
import multiprocessing
import os
import platform
import random
import re
import subprocess
import sys

from mininet.net import Mininet
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel

from SingleSwitchTopo import SingleSwitchTopo


# ---------------------------- GLOBAL CONSTANTS -------------------------------
ENVNAME = 0
REPORTNAME = 1

TIMESTAMP_ATTRS = {0: "TIMESTAMP_OUTPUT",
                   1: "tsLog.csv"}

SSH_CMD = 0
SSHD_PATH = 1
SSHPASS_CMD = 2
# Strictly speaking, the password is not a 'constant', but it is only set once
# throughout the lifetime of this script.
SSH_PASSWD = 3

SSH_ATTRS = {0: "ssh -oStrictHostKeyChecking=no mininet@",
             1: "/usr/sbin/sshd",
             2: "sshpass -p ",
             3: str()}

# ---------------------------- GLOBAL CONSTANTS -------------------------------


def tsTestPadMsgSize(padMsgSize, numOfRuns, msgSent):
    """
    Send 'msgSent' number of messages with 'padMsgSize' for each message.
    For now 'numOfRuns' parameter is IGNORED.
    """
    for argument in (padMsgSize, numOfRuns, msgSent):
        if not isinstance(argument, int) or 0 > argument:
            raise ValueError("argument must be non-negative integers")

    delta = list()
    normalized = list()
    padMsgSizeResult = list()
    tsOutput = str()
    tsCommand = "ts -s -b {0} -c {1} | {2} '{3}' {4}{5} ts -r -b {0} -c {1}"

    print("!! Performing TimeStamp Test Using Padding Message Size !!")
    topo = SingleSwitchTopo(n=2)
    net = Mininet(topo, link=TCLink)
    net.start()
    print("!! Dumping host connections !!")
    dumpNodeConnections(net.hosts)
    print("!! Testing network connectivity !!")
    net.pingAll()

    h1, h2 = net.getNodeByName("h1", "h2")
    h1.cmd(SSH_ATTRS[SSHD_PATH])
    h2.cmd(SSH_ATTRS[SSHD_PATH])
    print("!! Testing Time Delta/Normalized Arrival Time" +
          "Between h1 ({0}) and h2 ({1}) !!"
          .format(h1.IP(), h2.IP()))

    # From section 7.1.3 'Format String Syntax' of the official python doc:
    # https://docs.python.org/2/library/string.html
    print("Padding Message Size -------- [{0} byte]".format(str(padMsgSize)))
    tsOutput = h1.cmd(tsCommand
                      .format(padMsgSize, msgSent,
                              SSH_ATTRS[SSHPASS_CMD], SSH_ATTRS[SSH_PASSWD],
                              SSH_ATTRS[SSH_CMD], h2.IP()))
    # The extra splicing is used to remove the first line: which is
    # 'DELTA,NORMALIZED'.
    for pair in tsOutput.split()[1:]:
        delta.append(int(pair.split(",")[0]))
        normalized.append(int(pair.split(",")[1]))

    net.stop()
    padMsgSizeResult.append(delta)
    padMsgSizeResult.append(normalized)
    return padMsgSizeResult


def tsTestLoss(lossRate, numOfRuns, msgSent):
    """
    Send 'msgSent' number of messages with 'lossRate' between the two virtual
    hosts.
    For now 'numOfRuns' parameter is IGNORED.
    """
    for argument in (numOfRuns, msgSent):
        if not isinstance(argument, int) or 0 > argument:
            raise ValueError("numOfRuns msgSent must be non-negative integers")

    if not isinstance(lossRate, float) or .0 > lossRate:
        raise ValueError("lossRate must be non-negative integers")

    delta = list()
    normalized = list()
    lossResult = list()
    # Thanks Nooshin for giving proper instructions to properly use 'tc' and
    # avoid a potential pitfall!
    tcCommand = "tc qdisc add dev {0} root netem limit 10000000000 loss {1}%"
    tsCommand = "ts -s -c {0} | {1} '{2}' {3}{4} ts -r -c {0}"
    tsOutput = str()
    interfaceName = str()

    print("!! Performing TimeStamp Test Using Loss Rate !!")
    topo = SingleSwitchTopo(n=2)
    net = Mininet(topo, link=TCLink)
    net.start()
    print("!! Dumping host connections !!")
    dumpNodeConnections(net.hosts)
    print("!! Testing network connectivity !!")
    net.pingAll()

    h1, h2 = net.getNodeByName("h1", "h2")
    h1.cmd(SSH_ATTRS[SSHD_PATH])
    h2.cmd(SSH_ATTRS[SSHD_PATH])
    interfaceName = h1.cmd("ifconfig")
    # The interface name contains character '-', so adjustment is made to
    # account for that other than the word character class itself.
    interfaceName = re.findall(r"[\w'-]+", interfaceName)[0]
    print("!! Testing Time Delta/Normalized Arrival Time" +
          "Between h1 ({0}) and h2 ({1}) !!"
          .format(h1.IP(), h2.IP()))

    print("Loss Rate -------- [{0} %]".format(lossRate))
    h1.cmd(tcCommand.format(interfaceName, lossRate))
    tsOutput = h1.cmd(tsCommand.format(msgSent,
                                       SSH_ATTRS[SSHPASS_CMD],
                                       SSH_ATTRS[SSH_PASSWD],
                                       SSH_ATTRS[SSH_CMD],
                                       h2.IP()))
    for pair in tsOutput.split()[1:]:
        delta.append(int(pair.split(",")[0]))
        normalized.append(int(pair.split(",")[1]))

    net.stop()
    lossResult.append(delta)
    lossResult.append(normalized)
    return lossResult


def tsTestRTT(RTT, numOfRuns, msgSent):
    """
    Send 'msgSent' number of messages with 'RTT' set by mininet.
    For now 'numOfRuns' parameter is IGNORED.
    """
    for argument in (RTT, numOfRuns, msgSent):
        if not isinstance(argument, int) or 0 > argument:
            raise ValueError("argument must be non-negative integers")

    delta = list()
    normalized = list()
    RTTResult = list()
    tsCommand = "ts -s -c {0} | {1} '{2}' {3}{4} ts -r -c {0}"

    print("!! Performing TimeStamp Test Using RTT !!")
    # Note the RTT is indirectly set by the 'delay' option
    SingleSwitchTopo.setBuildOption("delay", RTT // 2)
    topo = SingleSwitchTopo(n=2)
    net = Mininet(topo, link=TCLink)
    net.start()
    print("!! Dumping host connections !!")
    dumpNodeConnections(net.hosts)
    print("!! Testing network connectivity !!")
    net.pingAll()

    h1, h2 = net.getNodeByName("h1", "h2")
    h1.cmd(SSH_ATTRS[SSHD_PATH])
    h2.cmd(SSH_ATTRS[SSHD_PATH])
    print("!! Testing Time Delta/Normalized Arrival Time" +
          "Between h1 ({0}) and h2 ({1}) !!"
          .format(h1.IP(), h2.IP()))

    print("RTT -------- [{0} ms]".format(str(RTT)))
    tsOutput = h1.cmd(tsCommand.format(msgSent,
                                       SSH_ATTRS[SSHPASS_CMD],
                                       SSH_ATTRS[SSH_PASSWD],
                                       SSH_ATTRS[SSH_CMD],
                                       h2.IP()))
    for pair in tsOutput.split()[1:]:
        delta.append(int(pair.split(",")[0]))
        normalized.append(int(pair.split(",")[1]))

    net.stop()
    RTTResult.append(delta)
    RTTResult.append(normalized)
    return RTTResult


def tsGenResult(test):
    """
    Clean up the report generated by the 'ts' program (if exists, even thoguh
    it is redundant to do so) and generates result list that should normally
    be passed to 'tsPlotResult' afterwards.
    Structure of Returned List
    [
        [
            [msgSent number of time deltas for one of MsgSize, Loss, RTT],
            [msgSent number of normalized time for one of MsgSize, Loss, RTT],
        ],
        ...
    ]
    """
    if not isinstance(test, str) or test not in ("padMsgSize", "loss", "RTT"):
        raise ValueError("argument must be string," +
                         "and one of padMsgSize, loss, RTT")
    os.system("cd /tmp/ && rm -f " + TIMESTAMP_ATTRS[REPORTNAME])
    # Environment variables set in the host will not be seen in the virtual
    # hosts set up by mininet, left as it is just in case
    os.system("export " + TIMESTAMP_ATTRS[ENVNAME] + "=" +
              TIMESTAMP_ATTRS[REPORTNAME])
    testResults = list()

    if "padMsgSize" == test:
        for padMsgSize in (2, 32, 512, 8192):
            testResults.append(tsTestPadMsgSize(padMsgSize, 1, 1024))
    elif "loss" == test:
        for lossRate in (0.1, 0.2, 0.3, 5):
            testResults.append(tsTestLoss(lossRate, 1, 1024))
    elif "RTT" == test:
        for RTT in (10, 30, 50, 70):
            testResults.append(tsTestRTT(RTT, 1, 1024))

    return testResults


def tsPlotResult(test, tsGenResultList):
    """
    Plot the result matrix according to only one of the metrics in padMsgSize,
    Loss, and RTT.
    Sample Structure of Plot Matrix for padMsgSize
    +--------------------------+---------------------------+
    |                          |                           |
    |Deltas when padMsgSize = 2|Deltas when padMsgSize = 32|
    |                          |                           |
    +--------------------------+---------------------------+
    |                          |                           |
    |   Normalized time when   |    Normalized time when   |
    |       padMsgSize = 2     |        padMsgSize = 32    |
    +--------------------------+---------------------------+
    """
    if not isinstance(test, str) or test not in ("padMsgSize", "loss", "RTT"):
        raise ValueError("test must be string," +
                         "and one of padMsgSize, loss, RTT")
    if not tsGenResultList or not isinstance(tsGenResultList, list):
        raise ValueError("tsGenResultList must be of list type " +
                         "and cannot be empty")

    outputPlotName = "tsTest" + test[0].upper() + test[1:] + ".png"
    plotDirectory = "./plot"
    # Based on an example from
    # http://matplotlib.org/examples/pylab_examples/subplots_demo.html
    fig, ((ax1, ax2, ax3, ax4), (ax5, ax6, ax7, ax8)) =\
        plt.subplots(2, 4, sharex="col", sharey="row")

    if "padMsgSize" == test:
        plt.suptitle("Timestamp Tests Using Padding Message Size")
    elif "loss" == test:
        plt.suptitle("Timestamp Tests Using Loss Rate")
    elif "RTT" == test:
        plt.suptitle("Timestamp Tests Using RTT")

    # There are lots of magic number 'hacks' in the following loop used for
    # plotting, which is a bad practice; but the author has limited experience
    # with matplotlib so it is kept this way (suggestions for better
    # alternatives?).
    for idx, subplot in enumerate((ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8)):
        subplot.axis([0, 1024, 0, 1024])
        subplot.grid(True)

        if 0 == idx:
            subplot.set_ylabel("Arrival Time Delta (millisecond)")
        if 4 == idx:
            subplot.set_ylabel("Normalized Arrival Time (millisecond)")

        if "padMsgSize" == test:
            if 0 == idx % 4:
                subplot.set_title("2 Bytes")
            if 1 == idx % 4:
                subplot.set_title("32 Bytes")
            if 2 == idx % 4:
                subplot.set_title("512 Bytes")
            if 3 == idx % 4:
                subplot.set_title("8192 Bytes")
        elif "loss" == test:
            if 0 == idx % 4:
                subplot.set_title("0.1 %")
            if 1 == idx % 4:
                subplot.set_title("0.2 %")
            if 2 == idx % 4:
                subplot.set_title("0.3 %")
            if 3 == idx % 4:
                subplot.set_title("5 %")
        elif "RTT" == test:
            if 0 == idx % 4:
                subplot.set_title("10 ms")
            if 1 == idx % 4:
                subplot.set_title("30 ms")
            if 2 == idx % 4:
                subplot.set_title("50 ms")
            if 3 == idx % 4:
                subplot.set_title("70 ms")

        # Plotting Deltas
        if 4 > idx:
            subplot.plot([i for i in range(0, 1024)],
                         tsGenResultList[idx % 4][0])
        # Plotting Normalized Time
        else:
            subplot.plot([i for i in range(0, 1024)],
                         tsGenResultList[idx % 4][1])

    plt.show()
    fig.savefig(outputPlotName)

    if (False == os.path.exists(plotDirectory)):
        os.mkdir(plotDirectory)

    os.system("mv " + outputPlotName + plotDirectory + "/")


def tsPrintResult(test, resultList):
    """
    Take result list for a test case specified and print 8 random samples from
    each single test.
    Since this script hardcoded 'Arrival Time Delta' and 'Normalized Arrival
    Time' for each test, in total there are 8 * 2 * 4 = 64 points.
    """
    if not isinstance(test, str) or test not in ("padMsgSize", "loss", "RTT"):
        raise ValueError("test must be string," +
                         "and one of padMsgSize, loss, RTT")
    if not resultList or not isinstance(resultList, list):
        raise ValueError("resultList must be of list type and cannot be empty")

    resultFileName = "ts" + test[0].upper() + test[1:] + "TestResult.txt"

    with open(resultFileName, "w") as resultFile:
        resultFile.write(test + "\n")

        # Pick one record at a time
        for dataPairIdx in range(len(resultList) * 2):
            sampleIdxList = list()
            currentRecord = list()

            if 0 == dataPairIdx:
                resultFile.write("Deltas|")
            elif len(resultList) == dataPairIdx:
                resultFile.write("Normalized|")

            # Arrival Time Deltas
            if len(resultList) > dataPairIdx:
                currentRecord = resultList[dataPairIdx][0]
            # Normalized Arrival Time -- wrap around back to the beginning
            else:
                currentRecord = resultList[dataPairIdx % len(resultList)][1]

            recordLen = len(currentRecord)
            sampleIdxList = tsPickSample(recordLen)

            for idx in sampleIdxList:
                outputPair = "[" + str(idx) + "," +\
                             str(currentRecord[idx]) + "]|"
                resultFile.write(outputPair)

            if (len(resultList) == dataPairIdx + 1):
                resultFile.write("\n")


def tsPickSample(recordListLength):
    """
    Pick 8 random indices within the close interval [0, recordListLength - 1]
    and return the picked indices in increasing sorted order.
    """
    if not isinstance(recordListLength, int) or 0 >= recordListLength:
        raise ValueError("recordListLength must be of int type and has size "
                         "greater than zero")

    sampleIdxList = list()
    # randint() uses close interval, so subtract 1 to account for that
    upperBound = recordListLength - 1

    while 8 != len(sampleIdxList):
        chosenIdx = random.randint(0, upperBound)
        if chosenIdx in sampleIdxList:
            continue
        else:
            sampleIdxList.append(chosenIdx)

    sampleIdxList.sort()
    return sampleIdxList


def autoGen():
    """
    Automatically generates the binary of the timestamp program using a
    combination of cmake and make commands.
    Note when used in the mininet ubuntu 14.04 LTS VM, gcc has to be updated
    to the newest version according to the instructions given in the top level
    README.md file, otherwise this function would not work properly.
    """

    buildDirectory = "./build"
    logicalCPUCount = str(multiprocessing.cpu_count() + 1)
    # Note the cmake commands used are not shown in official documentation:
    # '-B' specifies the build directory
    # '-H' specifies the source directory
    cmakeCommands = ["cmake", "-B" + buildDirectory, "-H."]
    makeCommands = ["make", "-j", logicalCPUCount,
                    "-C", buildDirectory, "install"]

    # Define extra macros for cmake to find compilers that support c++11
    # if inside the mininet ubuntu 14.04 LTS VM
    if "mininet-vm" == platform.node():
        cmakeCommands.append("-DCMAKE_C_COMPILER=/usr/bin/gcc-5")
        cmakeCommands.append("-DCMAKE_CXX_COMPILER=/usr/bin/g++-5")

    # Make a new build directory if it does not exist
    if (False == os.path.exists(buildDirectory)):
        os.mkdir(buildDirectory)
    elif (True == os.path.isdir(buildDirectory)):
        os.system("rm -rf " + buildDirectory + "/*")
    # There is a file named build otherwise
    elif (False == os.path.isdir(buildDirectory)):
        sys.exit("Name conflicts for the \"" + buildDirectory + "\"!")

    subprocess.call(cmakeCommands)
    subprocess.call(makeCommands)


if __name__ == "__main__":
    tsTestDescription = "Perform a series of Tests using the Timestamp (ts)" +\
                        " Program to Measure Time Difference and Normalized" +\
                        " Arrival Time under 3 Metrics: Padding Message " +\
                        "Size, Loss Rate, and RTT"
    passPrompt = "Password used for SSH among mininet virtual hosts: "

    if "posix" != os.name:
        sys.exit("This script is only mean to be used on POSIX systems.")

    setLogLevel("info")

    parser = argparse.ArgumentParser(description=tsTestDescription)
    parser.add_argument("-b",
                        "--build",
                        action="store_true",
                        help="Build the Timestamp Executable",
                        required=False)
    args = parser.parse_args()

    if args.build:
        autoGen()

    SSH_ATTRS[SSH_PASSWD] = getpass.getpass(passPrompt)
    #tsPlotResult("padMsgSize", tsGenResult("padMsgSize"))
    #tsPlotResult("RTT", tsGenResult("RTT"))
    #tsPlotResult("loss", tsGenResult("loss"))
    tsPrintResult("padMsgSize", tsGenResult("padMsgSize"))
