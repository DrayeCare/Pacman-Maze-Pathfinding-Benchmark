"""Biaya sel opsional untuk pathfinding.

Tanpa biaya, semua sel berharga 1 dan algoritma berperilaku persis seperti
versi awal. Biaya minimal 1 supaya heuristik Manhattan tetap admissible.
"""


def biaya_sel(biaya, r, c):
    """Biaya untuk masuk ke sel (r, c); default 1."""
    if not biaya:
        return 1
    try:
        if isinstance(biaya, dict):
            nilai = biaya.get((int(r), int(c)), 1)
        else:
            nilai = biaya[int(r)][int(c)]
        nilai = int(nilai)
    except (KeyError, IndexError, TypeError, ValueError):
        return 1
    return max(1, nilai)


def ada_biaya(biaya):
    """True hanya jika ada sel dengan biaya lebih dari 1."""
    if not biaya:
        return False
    try:
        if isinstance(biaya, dict):
            return any(int(v) > 1 for v in biaya.values())
        return any(int(v) > 1 for baris in biaya for v in baris)
    except (TypeError, ValueError):
        return False
