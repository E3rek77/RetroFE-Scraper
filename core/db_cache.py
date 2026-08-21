"""
Invalidation du cache meta.db de RetroFE.

RetroFE met en cache les métadonnées de chaque collection dans un fichier
meta.db à la racine de l'installation. Après avoir ajouté/modifié des médias
ou des descriptions, il faut forcer RetroFE à reconstruire ce cache, sinon
les changements ne sont pas pris en compte au prochain lancement.

La convention (observée et utilisée manuellement sur ce projet) est de
renommer meta.db en meta.db.bak<N> plutôt que de le supprimer, pour rester
réversible.
"""
from __future__ import annotations

import os
import glob


def invalidate_meta_db(retrofe_root: str) -> str | None:
    """Renomme meta.db en meta.db.bakN (N = premier numéro libre).
    Retourne le nouveau nom de fichier, ou None si meta.db n'existe pas."""
    meta_db = os.path.join(retrofe_root, "meta.db")
    if not os.path.isfile(meta_db):
        return None

    existing = glob.glob(os.path.join(retrofe_root, "meta.db.bak*"))
    existing_nums = []
    for path in existing:
        suffix = os.path.basename(path).replace("meta.db.bak", "")
        if suffix == "":
            existing_nums.append(1)
        elif suffix.isdigit():
            existing_nums.append(int(suffix))
    next_num = (max(existing_nums) + 1) if existing_nums else 1
    suffix = "" if next_num == 1 and not existing_nums else str(next_num)
    new_name = os.path.join(retrofe_root, f"meta.db.bak{suffix}")

    os.rename(meta_db, new_name)
    return new_name
