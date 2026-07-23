import numpy as np
import json
import argparse
from pathlib import Path
from tqdm import tqdm

# ------------------ Globals ------------------
num2aa=[
    'ALA','ARG','ASN','ASP','CYS','GLN','GLU','GLY','HIS','ILE',
    'LEU','LYS','MET','PHE','PRO','SER','THR','TRP','TYR','VAL',
]
aa2long=[ # 14 possible atoms
    (" N  "," CA "," C  "," O  "," CB ",  None,  None,  None,  None,  None,  None,  None,  None,  None), # ala
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD "," NE "," CZ "," NH1"," NH2",  None,  None,  None), # arg
    (" N  "," CA "," C  "," O  "," CB "," CG "," OD1"," ND2",  None,  None,  None,  None,  None,  None), # asn
    (" N  "," CA "," C  "," O  "," CB "," CG "," OD1"," OD2",  None,  None,  None,  None,  None,  None), # asp
    (" N  "," CA "," C  "," O  "," CB "," SG ",  None,  None,  None,  None,  None,  None,  None,  None), # cys
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD "," OE1"," NE2",  None,  None,  None,  None,  None), # gln
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD "," OE1"," OE2",  None,  None,  None,  None,  None), # glu
    (" N  "," CA "," C  "," O  ",  None,  None,  None,  None,  None,  None,  None,  None,  None,  None), # gly
    (" N  "," CA "," C  "," O  "," CB "," CG "," ND1"," CD2"," CE1"," NE2",  None,  None,  None,  None), # his
    (" N  "," CA "," C  "," O  "," CB "," CG1"," CG2"," CD1",  None,  None,  None,  None,  None,  None), # ile
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD1"," CD2",  None,  None,  None,  None,  None,  None), # leu
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD "," CE "," NZ ",  None,  None,  None,  None,  None), # lys
    (" N  "," CA "," C  "," O  "," CB "," CG "," SD "," CE ",  None,  None,  None,  None,  None,  None), # met
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD1"," CD2"," CE1"," CE2"," CZ ",  None,  None,  None), # phe
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD ",  None,  None,  None,  None,  None,  None,  None), # pro
    (" N  "," CA "," C  "," O  "," CB "," OG ",  None,  None,  None,  None,  None,  None,  None,  None), # ser
    (" N  "," CA "," C  "," O  "," CB "," OG1"," CG2",  None,  None,  None,  None,  None,  None,  None), # thr
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD1"," CD2"," CE2"," CE3"," NE1"," CZ2"," CZ3"," CH2"), # trp
    (" N  "," CA "," C  "," O  "," CB "," CG "," CD1"," CD2"," CE1"," CE2"," CZ "," OH ",  None,  None), # tyr
    (" N  "," CA "," C  "," O  "," CB "," CG1"," CG2",  None,  None,  None,  None,  None,  None,  None), # val
]
aa2num= {x:i for i,x in enumerate(num2aa)}
alpha_1 = list("ARNDCQEGHILKMFPSTWYV-")
aa123 = {aa1: aa3 for aa1, aa3 in zip(alpha_1, num2aa)}

# ------------------ PDB Parsing ------------------
def parse_pdb_lines(lines, parse_hetatom=False, ignore_het_h=True):
    res = [(l[22:26], l[17:20]) for l in lines if l[:4]=="ATOM" and l[12:16].strip()=="CA"]
    seq = [aa2num.get(r[1], 20) for r in res]
    pdb_idx = [(l[21:22].strip(), int(l[22:26].strip())) for l in lines if l[:4]=="ATOM" and l[12:16].strip()=="CA"]

    xyz = np.full((len(res), 14, 3), np.nan, dtype=np.float32)
    for l in lines:
        if not l.startswith("ATOM"): continue
        chain, resNo, atom, aa = l[21:22], int(l[22:26]), l[12:16].strip(), l[17:20]
        idx = pdb_idx.index((chain, resNo))
        for i_atm, tgtatm in enumerate(aa2long[aa2num.get(aa, 0)]):
            if tgtatm and tgtatm.strip() == atom.strip():
                xyz[idx, i_atm, :] = [float(l[30:38]), float(l[38:46]), float(l[46:54])]
                break

    mask = ~np.isnan(xyz[...,0])
    xyz[np.isnan(xyz)] = 0.0

    # remove duplicates
    new_idx, i_unique = [], []
    for i, idx in enumerate(pdb_idx):
        if idx not in new_idx:
            new_idx.append(idx)
            i_unique.append(i)
    pdb_idx = new_idx
    xyz = xyz[i_unique]
    mask = mask[i_unique]
    seq = np.array(seq)[i_unique]

    out = {'xyz': xyz, 'mask': mask, 'idx': np.array([i[1] for i in pdb_idx]),
           'seq': seq, 'pdb_idx': pdb_idx, 'plddt_val': []}

    if parse_hetatom:
        xyz_het, info_het = [], []
        for l in lines:
            if l.startswith("HETATM") and not (ignore_het_h and l[76:78].strip() == "H"):
                atom_name = l[12:16].strip()
                resname = l[17:20].strip()
                chain = l[21:22].strip() or "A"
                resnum = int(l[22:26])
                elem = l[76:78].strip() or atom_name[0]
                xyz_het.append([float(l[30:38]), float(l[38:46]), float(l[46:54])])
                info_het.append({'chain': chain, 'resnum': resnum, 'atom_id': atom_name,
                                 'atom_type': elem, 'resname': resname})
        if xyz_het:
            out['xyz_het'] = np.array(xyz_het)
            out['info_het'] = info_het
    return out

def parse_pdb(fn, **kwargs):
    return parse_pdb_lines(open(fn).readlines(), **kwargs)

# ------------------ PDB Writing ------------------
def write_pdb_string(xyz, res, pdb_idx=None):
    if pdb_idx is None:
        pdb_idx = [('A', i+1) for i in range(len(res))]
    wrt = ""
    atmNo = 0
    for i_res, (ch,i_pdb), aa in zip(range(len(res)), pdb_idx, res):
        for i_atm, atm in enumerate(["N","CA","C","O"]):
            atmNo += 1
            wrt += "ATOM  %5d %4s %3s %s%4d    %8.3f%8.3f%8.3f%6.2f%6.2f\n"%(
                atmNo, atm, aa123[aa], ch, i_pdb,
                xyz[i_res,i_atm,0], xyz[i_res,i_atm,1], xyz[i_res,i_atm,2], 1.0, 0.0)
    return wrt

def write_pdb(xyz, prefix, res, pdb_idx=None, xyz_het=None, info_het=None):
    wrt = write_pdb_string(xyz, res, pdb_idx)
    with open(prefix,'w') as fp:
        fp.write(wrt)
        fp.write("\n")
        if xyz_het is not None and len(xyz_het) > 0:
            fp.write("\n")
            for i, (het, info) in enumerate(zip(xyz_het, info_het), 1): #type: ignore
                elem = info['atom_type'].rjust(2)
                fp.write(
                    "HETATM{:5d} {:>4s} {:>3s} {}{:4d}    {:8.3f}{:8.3f}{:8.3f}  1.00  0.00           {:>2s}\n".format(
                        i,                  # serial number (just sequential)
                        info['atom_id'],    # atom name
                        info['resname'],    # ligand name
                        info['chain'],      # chain
                        info['resnum'],     # residue number
                        het[0], het[1], het[2],
                        elem
                    )
                )
# ------------------ Main ------------------
def combine_pdbs(pdb_fn1, pdb_fn2, out_fn):
    pdb1 = parse_pdb(pdb_fn1, parse_hetatom=True)
    pdb2 = parse_pdb(pdb_fn2, parse_hetatom=True)

    # chain B and translate
    pdb2['pdb_idx'] = [('B', i[1]) for i in pdb2['pdb_idx']]
    pdb2['xyz'] += np.array([300,0,0],dtype=np.float32)

    # Combine
    pdb_comb = {}
    pdb_comb['xyz'] = np.concatenate([pdb1['xyz'], pdb2['xyz']], axis=0)
    #pdb_comb['pdb_idx'] = np.concatenate([pdb1['pdb_idx'], pdb2['pdb_idx']], axis=0)
    pdb_comb['pdb_idx'] = [ (str(ch), int(res)) for ch,res in list(pdb1['pdb_idx']) + list(pdb2['pdb_idx']) ]
    pdb_comb['seq'] = np.concatenate([pdb1['seq'], pdb2['seq']], axis=0)

    # Combine ligands
    xyz_het_list, info_het_list = [], []
    if 'xyz_het' in pdb1: xyz_het_list.append(pdb1['xyz_het']); info_het_list += pdb1['info_het']
    if 'xyz_het' in pdb2:
        xyz_het_list.append(pdb2['xyz_het'] + np.array([300,0,0],dtype=np.float32))
        info_het_list += pdb2['info_het']
    if xyz_het_list:
        pdb_comb['xyz_het'] = np.concatenate(xyz_het_list, axis=0)
        pdb_comb['info_het'] = info_het_list

    # write
    write_pdb(pdb_comb['xyz'], out_fn, [alpha_1[e] for e in pdb_comb['seq']],
              pdb_idx=pdb_comb['pdb_idx'],
              xyz_het=pdb_comb.get('xyz_het'),
              info_het=pdb_comb.get('info_het'))

def main():
    parser = argparse.ArgumentParser(
        description = "Combine 2 PDB files (e.g. 2 different states of a protein) into one for ProteinMPNN homooligomer design"
    )
    parser.add_argument(
        "input",
        type=str,
        help='.json file formatted with keys = path to state A, values = path to state B'
    )
    args = parser.parse_args()

    # process each pair in .json file
    with open(args.input, 'r') as file:
        inputs = json.load(file)
    
    outputs = {}
    for input in tqdm(inputs):
        pdb_fn1 = input
        pdb_fn2 = inputs[input]
        out_fn = Path.joinpath(Path(args.input).parent, f'{Path(input).stem}_combined.pdb')
        combine_pdbs(
            pdb_fn1,
            pdb_fn2,
            out_fn
        )
        outputs[f'{out_fn}'] = ''
    
    with open(Path.joinpath(Path(args.input).parent, f'{Path(args.input).stem}_combined.json'), 'w') as file:
        json.dump(outputs, file)
    
    print(f"Combined {len(outputs)} PDB files")

if __name__ == "__main__":
    main()

