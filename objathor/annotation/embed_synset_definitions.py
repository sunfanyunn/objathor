import random
from typing import Dict
import os

import compress_pickle
import numpy as np
from tqdm import tqdm

from objathor.utils.gpt_utils import get_embedding
from objathor.utils.synsets import (
    all_synsets,
    synset_definitions,
    synset_lemmas,
    synset_hyponyms,
    synset_hypernyms,
)


def get_embeddings(
    fname: str = "data/synset_definition_embeddings.pkl.gz",
) -> Dict[str, np.ndarray]:
    if os.path.isfile(fname):
        data = compress_pickle.load(fname)
    else:
        data = {}

    num_additions = 0
    try:
        for synset_str in tqdm(all_synsets()):
            if synset_str in data:
                continue
            definition = synset_definitions([synset_str])[0]
            embedding = get_embedding(definition)
            data[synset_str] = np.array(embedding) / np.linalg.norm(embedding)
            num_additions += 1
    finally:
        if num_additions > 0:
            print("Saving definition embeddings...")
            compress_pickle.dump(data, fname)

    return data


def get_embeddings_single(
    fname: str = "data/synset_definition_embeddings_single.pkl.gz",
) -> Dict[str, np.ndarray]:
    if not os.path.isfile(fname):
        data = get_embeddings()
        for key, value in data.items():
            data[key] = value.astype(np.float32)
        compress_pickle.dump(data, fname)
    else:
        data = compress_pickle.load(fname)

    return data


def local_smoothing(embs: Dict[str, np.ndarray], synset_str: str):
    ref = embs[synset_str]
    from nltk.corpus import wordnet2022 as wn

    comb = [ref]

    hypos = wn.synset(synset_str).hyponyms()
    print("hypos", [syn.name() for syn in hypos])
    if len(hypos) > 0:
        hypos = np.stack([embs[syn.name()] for syn in hypos], axis=1)
        hypo_mean = hypos.sum(axis=1)
        comb.append(0.5 * hypo_mean / np.linalg.norm(hypo_mean))

    hypers = wn.synset(synset_str).hypernyms()
    print("hypers", [syn.name() for syn in hypers])
    if len(hypers) > 0:
        hypers = np.stack([embs[syn.name()] for syn in hypers], axis=1)
        hyper_mean = hypers.sum(axis=1)
        comb.append(0.5 * hyper_mean / np.linalg.norm(hyper_mean))

    comb = np.sum(comb, axis=0)
    comb = comb / np.linalg.norm(comb)

    if len(hypos) > 0:
        print("ref, hypos", ref @ hypos, np.mean(ref @ hypos))

    if len(hypers) > 0:
        print("ref, hypers", ref @ hypers, np.mean(ref @ hypers))

    if len(hypos) > 0 and len(hypers) > 0:
        print("hypos, hypers", hypos.T @ hypers, np.mean(hypos.T @ hypers))

    print("ref, comb", ref @ comb, np.mean(ref @ comb))

    if len(hypos) > 0:
        print("comb, hypos", comb @ hypos, np.mean(comb @ hypos))

    if len(hypers) > 0:
        print("comb, hypers", comb @ hypers, np.mean(comb @ hypers))


def get_lemmas_definition_embeddings(
    fname: str = "data/synset_lemmas_definitions_embeddings.pkl.gz", max_lemmas: int = 3
) -> Dict[str, np.ndarray]:
    if os.path.isfile(fname):
        data = compress_pickle.load(fname)
    else:
        data = {}

    def format_lemmas(lemmas):
        lemmas = [f'{lemma.replace("_", " ")}' for lemma in lemmas]

        if len(lemmas) == 0:
            formatted_lemmas = ""
        elif len(lemmas) == 1:
            formatted_lemmas = f"{lemmas[0]}"
        elif len(lemmas) == 2:
            formatted_lemmas = f"{lemmas[0]} or {lemmas[1]}"
        else:
            formatted_lemmas = ", ".join(lemmas[:-1]) + f", or {lemmas[-1]}"

        return formatted_lemmas

    num_additions = 0
    try:
        for synset_str in tqdm(all_synsets()):
            if synset_str in data:
                continue

            lemmas = synset_lemmas([synset_str])[0][:max_lemmas]
            formatted_lemmas = format_lemmas(lemmas)

            lemmas = set(lemmas)

            hyper = (
                set(
                    sum(
                        [
                            synset_lemmas([hyp.name()])[0]
                            for hyp in synset_hypernyms([synset_str])[0]
                        ],
                        [],
                    )
                )
                - lemmas
            )
            hyper = list(hyper)
            random.shuffle(hyper)
            hyper = hyper[:max_lemmas]

            hyper_lemmas = format_lemmas(hyper)

            hyper = set(hyper)

            hypo = (
                set(
                    sum(
                        [
                            synset_lemmas([hyp.name()])[0]
                            for hyp in synset_hyponyms([synset_str])[0]
                        ],
                        [],
                    )
                )
                - lemmas
                - hyper
            )
            hypo = list(hypo)
            random.shuffle(hypo)
            hypo = hypo[:max_lemmas]

            hypo_lemmas = format_lemmas(hypo)

            context = ""
            if len(hypo_lemmas) > 0 and len(hyper_lemmas) > 0:
                context = f", a type of {hyper_lemmas} like {hypo_lemmas}"
            elif len(hyper_lemmas) > 0:
                context = f", a type of {hyper_lemmas}"
            elif len(hypo_lemmas) > 0:
                context = f", like {hypo_lemmas}"

            text = f"{formatted_lemmas}{context}; {synset_definitions([synset_str])[0]}"

            embedding = get_embedding(text)
            data[synset_str] = dict(
                emb=(np.array(embedding) / np.linalg.norm(embedding)).astype(
                    np.float32
                ),
                text=text,
            )

            num_additions += 1
            if num_additions == 1000:
                print(f"Saving definition embeddings with {len(data)} entries...")
                compress_pickle.dump(data, fname)
                num_additions = 0
    finally:
        if num_additions > 0:
            print(f"Saving definition embeddings with {len(data)} entries...")
            compress_pickle.dump(data, fname)

    return data


if __name__ == "__main__":
    # data = get_embeddings()
    # data = get_embeddings_single()
    # local_smoothing(data, "wardrobe.n.01")

    data = get_lemmas_definition_embeddings()
    print("DONE")