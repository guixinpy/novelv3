from app.models import Outline, Setup
from app.schemas import TopologyEdge, TopologyNode


class TopologyBuilder:
    def build(self, project_id: str, setup: Setup, outline: Outline | None) -> dict:
        nodes = []
        edges = []
        node_map = {}

        for char in setup.characters or []:
            name = char.get("name")
            if not name:
                continue
            nid = f"char_{name}"
            nodes.append(TopologyNode(id=nid, type="CHARACTER", label=name, meta={"appearance_count": 0, "last_chapter": 0}).model_dump())
            node_map[nid] = True

        if outline and outline.chapters:
            for ch in outline.chapters:
                title = ch.get("title", f"第{ch.get('chapter_index')}章")
                nid = f"evt_{ch.get('chapter_index')}"
                nodes.append(TopologyNode(id=nid, type="EVENT", label=title, meta={"chapter_index": ch.get("chapter_index")}).model_dump())
                node_map[nid] = True

                for char_name in ch.get("characters", []):
                    cid = f"char_{char_name}"
                    if cid in node_map:
                        edges.append(TopologyEdge(id=f"app_{ch.get('chapter_index')}_{char_name}", source=cid, target=nid, type="appearance", meta={}).model_dump())

        return {
            "project_id": project_id,
            "version": 1,
            "nodes": nodes,
            "edges": edges,
            "indexes": {},
        }
