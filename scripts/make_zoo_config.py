"""Select Topology Zoo networks (>= 15 nodes, coordinates for >= 95% of nodes) and write configs/default.toml.

    python scripts/make_zoo_config.py path/to/topologyzoo/sources

Copies the chosen GML files into data/topology_zoo/ (Internet Topology Zoo, CC BY, Knight et al. 2011).
"""
import shutil
import sys
from pathlib import Path

from multipath_eval.topologies import has_coordinates, load_network

src = Path(sys.argv[1])
root = Path(__file__).resolve().parents[1]
dest = root / "data" / "topology_zoo"
dest.mkdir(parents=True, exist_ok=True)
for old in dest.glob("*"):
    old.unlink()
chosen = []
for f in sorted(src.glob("*.gml")):
    try:
        g = load_network(f)
    except Exception as exc:  # unparsable file
        print("skip", f.name, exc)
        continue
    if g.number_of_nodes() >= 15 and has_coordinates(g) and g.number_of_edges() >= g.number_of_nodes():
        shutil.copy(f, dest / f.name)
        chosen.append(f.stem)
head = (root / "configs" / "header.toml").read_text(encoding="utf-8")
body = "".join(
    f'\n[[topologies]]\nname = "{n}"\nfamily = "gml"\npath = "data/topology_zoo/{n}.gml"\nseeds = 1\n' for n in chosen
)
(root / "configs" / "default.toml").write_text(head + body, encoding="utf-8")
print(len(chosen), "networks")
