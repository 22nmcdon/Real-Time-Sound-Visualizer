import re, json
src = open("/home/user/Real-Time-Sound-Visualizer/core/include/scope/presets.h").read()
pieces = re.findall(r'R"preset\((.*?)\)preset"', src, re.S)
lib = json.loads("".join(pieces))
BANK = {e[0]: e[1] for sec in lib for e in sec[1]}
