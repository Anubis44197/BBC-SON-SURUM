import os
import time
import hashlib
import pandas as pd
import numpy as np
import psutil
import scipy.stats as stats
from collections import Counter

# ===============================
# KULLANICI AYARLARI
# ===============================
# Göreceli yol kullanarak taşınabilir hale getirildi
# Test dosyası için örnek yol - kendi dosyanızı buraya koyun
FILENAME = os.path.join(os.path.dirname(__file__), "..", "test_data", "CHINESE_INSTRUCT_READY.parquet")
TOP_RECIPES = 20
SEEDS = [42, 123, 777, 999, 2024]
CORRUPTION_SEED = 888
CORRUPTION_RATIO = 0.2
OPERATORS = ['+', '-', '*', '/', '^', '=', 'sin', 'cos', 'int', 'dx', 'sqrt', 'log', 'sum', 'lim']

# ===============================
# YARDIMCI FONKSİYONLAR
# ===============================
def file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def get_operators(text):
    text = str(text)
    ops = set()
    for op in OPERATORS:
        if op in text.lower():
            ops.add(op)
    return ops

def get_operator_signature(text):
    return frozenset(get_operators(text))

def analyze_steps(text):
    text = str(text)
    return len([L for L in text.split('\n') if len(L.strip()) > 5])

def calculate_consistency_score(df_subset):
    if len(df_subset) < 2:
        return 0.0
    
    op_sets, step_counts = [], []
    for _, row in df_subset.iterrows():
        resp = str(row['response'])
        op_sets.append(get_operators(resp))
        step_counts.append(analyze_steps(resp))
    
    # Jaccard Index
    jaccard_scores = []
    for i in range(len(op_sets)):
        for j in range(i+1, len(op_sets)):
            u = op_sets[i].union(op_sets[j])
            jaccard_scores.append(len(op_sets[i].intersection(op_sets[j])) / len(u) if u else 0)
    mean_jaccard = np.mean(jaccard_scores) if jaccard_scores else 0
    
    # Step Consistency
    steps_array = np.array(step_counts)
    mean_steps, std_steps = np.mean(steps_array), np.std(steps_array)
    step_consistency = 1.0 / (1.0 + std_steps / mean_steps) if mean_steps > 0 else 0
    
    return mean_jaccard * 0.7 + step_consistency * 0.3

def calculate_strict_score(df_subset):
    if len(df_subset) < 2:
        return 0
    
    lengths = df_subset['response'].astype(str).str.len().values
    cv = np.std(lengths) / np.mean(lengths) if np.mean(lengths) > 0 else 0
    length_score = 1.0 / (1.0 + cv)
    
    op_counts = [get_operators(str(t)) for t in df_subset['response']]
    if not op_counts:
        return 0
    intersection = set.intersection(*op_counts) if op_counts else set()
    union = set.union(*op_counts) if op_counts else set()
    op_score = len(intersection) / len(union) if union else 0
    
    return 0.4 * length_score + 0.6 * op_score

# ===============================
# ANA PIPELINE
# ===============================
def run_pipeline():
    print("="*80)
    print("BBC HMPU COMPREHENSIVE VALIDATION PIPELINE")
    print("="*80)
    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    report = []
    process = psutil.Process()
    
    # ========== STEP 1: VERI KONTROLÜ ==========
    print("[STEP 1] VERI KONTROLÜ")
    print("-"*80)
    
    if not os.path.exists(FILENAME):
        print(f"FATAL: Dosya yok -> {FILENAME}")
        return
    
    size_bytes = os.path.getsize(FILENAME)
    print(f"Dosya Boyutu: {size_bytes:,} bytes ({size_bytes/(1024**2):.2f} MB)")
    
    start_hash = time.perf_counter()
    sha256 = file_hash(FILENAME)
    hash_time = time.perf_counter() - start_hash
    print(f"SHA256: {sha256}")
    print(f"Hash Süresi: {hash_time:.3f} sec")
    
    ram_before = process.memory_info().rss / (1024*1024)
    start_load = time.perf_counter()
    
    try:
        df = pd.read_parquet(FILENAME, engine='pyarrow')
    except Exception as e:
        print(f"FATAL: Yükleme hatası: {e}")
        return
    
    load_time = time.perf_counter() - start_load
    ram_after = process.memory_info().rss / (1024*1024)
    ram_increase = ram_after - ram_before
    
    total_rows = len(df)
    unique_groups = df['subject'].astype(str).str.cat(df['difficulty'].astype(str), sep="::").nunique()
    
    print(f"Yükleme Süresi: {load_time:.3f} sec")
    print(f"RAM Öncesi: {ram_before:.2f} MB")
    print(f"RAM Sonrası: {ram_after:.2f} MB")
    print(f"RAM Artışı: {ram_increase:.2f} MB")
    print(f"Toplam Satır: {total_rows:,}")
    print(f"Benzersiz Grup: {unique_groups}")
    
    report.append({
        "Test": "VERI KONTROLÜ",
        "Dosya_Boyutu": size_bytes,
        "SHA256": sha256,
        "Hash_Süresi": hash_time,
        "Yükleme_Süresi": load_time,
        "RAM_Artışı": ram_increase,
        "Satır_Sayısı": total_rows,
        "Benzersiz_Grup": unique_groups,
        "Sonuç": "TAMAMLANDI"
    })
    
    # ========== STEP 2: RAW COMPUTE BENCHMARK ==========
    print(f"\n[STEP 2] RAW COMPUTE BENCHMARK")
    print("-"*80)
    
    process.cpu_percent(interval=None)  # İlk ölçüm
    
    start_iter = time.perf_counter()
    questions = df['question'].astype(str).tolist()
    total_chars = sum(len(q) for q in questions)
    iter_time = time.perf_counter() - start_iter
    
    avg_len = total_chars / len(questions) if questions else 0
    cpu_usage = process.cpu_percent(interval=None)
    ram_used = process.memory_info().rss / (1024*1024)
    
    print(f"Toplam Satır: {len(questions):,}")
    print(f"Toplam Karakter: {total_chars:,}")
    print(f"Ortalama Uzunluk: {avg_len:.2f} karakter")
    print(f"İterasyon Süresi: {iter_time:.6f} sec")
    print(f"CPU Kullanımı: {cpu_usage:.2f}%")
    print(f"RAM Kullanımı: {ram_used:.2f} MB")
    
    report.append({
        "Test": "RAW COMPUTE BENCHMARK",
        "Toplam_Satır": len(questions),
        "Toplam_Karakter": total_chars,
        "Ortalama_Uzunluk": avg_len,
        "İterasyon_Süresi": iter_time,
        "CPU_Kullanımı": cpu_usage,
        "RAM_Kullanımı": ram_used,
        "Sonuç": "TAMAMLANDI"
    })
    
    # ========== STEP 3: RECIPE CONSISTENCY CHECK ==========
    print(f"\n[STEP 3] RECIPE CONSISTENCY CHECK")
    print("-"*80)
    
    df['recipe_id'] = df['subject'].astype(str) + "::" + df['difficulty'].astype(str)
    top_recipes = df['recipe_id'].value_counts().head(TOP_RECIPES).index.tolist()
    
    consistency_results = []
    for i, recipe in enumerate(top_recipes[:min(3, len(top_recipes))], 1):
        subset = df[df['recipe_id'] == recipe]
        sample = subset.sample(min(5, len(subset)), random_state=42)
        
        steps = [analyze_steps(r['response']) for _, r in sample.iterrows()]
        op_sets = [get_operators(r['response']) for _, r in sample.iterrows()]
        
        mean_steps, std_steps = np.mean(steps), np.std(steps)
        cv = std_steps / mean_steps if mean_steps > 0 else 0
        
        union_ops = set.union(*op_sets) if op_sets else set()
        intersection_ops = set.intersection(*op_sets) if op_sets else set()
        jaccard = len(intersection_ops) / len(union_ops) if union_ops else 0
        
        status = "PASS" if cv <= 1.2 and jaccard >= 0.15 else "FAIL"
        
        print(f"Recipe {i}: {recipe}")
        print(f"  Mean Steps: {mean_steps:.1f}, Std: {std_steps:.2f}, CV: {cv:.2f}")
        print(f"  Jaccard: {jaccard:.2f}, Status: {status}")
        
        consistency_results.append({
            "Recipe": recipe,
            "Mean_Steps": mean_steps,
            "CV": cv,
            "Jaccard": jaccard,
            "Status": status
        })
    
    final_consistency = "PASS" if all(r['Status'] == 'PASS' for r in consistency_results) else "MIXED"
    
    report.append({
        "Test": "RECIPE CONSISTENCY",
        "Details": consistency_results,
        "Sonuç": final_consistency
    })
    
    # ========== STEP 4: RECIPE FALSIFICATION TEST ==========
    print(f"\n[STEP 4] RECIPE FALSIFICATION TEST")
    print("-"*80)
    
    # Solution Validity Check
    sample_100 = df.sample(min(100, len(df)), random_state=42)
    validity = sum(1 for _, r in sample_100.iterrows()
                   if analyze_steps(r['response']) >= 2 and len(get_operators(r['response'])) >= 1) / len(sample_100)
    
    print(f"Solution Validity: {validity*100:.1f}%")
    
    # Real vs Random
    real_scores = []
    for r in top_recipes[:20]:
        subset = df[df['recipe_id'] == r]
        if len(subset) >= 10:
            sample = subset.sample(10, random_state=42)
            score = calculate_consistency_score(sample)
            real_scores.append(score)
    
    random_scores = [calculate_consistency_score(df.sample(10, random_state=i)) 
                     for i in range(len(real_scores))]
    
    mean_real, mean_rand = np.mean(real_scores), np.mean(random_scores)
    diff = mean_real - mean_rand
    t_stat, p_val = stats.ttest_ind(real_scores, random_scores, equal_var=False)
    
    result = "PASS" if diff > 0.1 and p_val < 0.05 and validity >= 0.8 else "FAIL"
    
    print(f"Mean Real: {mean_real:.4f}")
    print(f"Mean Random: {mean_rand:.4f}")
    print(f"Difference: {diff:.4f}")
    print(f"T-Stat: {t_stat:.2f}, P-Value: {p_val:.6f}")
    print(f"Result: {result}")
    
    report.append({
        "Test": "FALSIFICATION",
        "Validity": validity,
        "Mean_Real": mean_real,
        "Mean_Random": mean_rand,
        "Difference": diff,
        "P_Value": p_val,
        "Sonuç": result
    })
    
    # ========== STEP 5: STRICT FALSIFICATION ==========
    print(f"\n[STEP 5] STRICT FALSIFICATION TEST")
    print("-"*80)
    
    strict_real = []
    for r in top_recipes[:20]:
        subset = df[df['recipe_id'] == r]
        if len(subset) >= 20:
            sample = subset.sample(20, random_state=42)
            score = calculate_strict_score(sample)
            strict_real.append(score)
    
    strict_random = [calculate_strict_score(df.sample(20, random_state=200+i)) 
                     for i in range(len(strict_real))]
    
    mean_real_strict = np.mean(strict_real)
    mean_rand_strict = np.mean(strict_random)
    diff_strict = mean_real_strict - mean_rand_strict
    t_stat_strict, p_val_strict = stats.ttest_ind(strict_real, strict_random, equal_var=False)
    
    result_strict = "PASS" if diff_strict > 0.1 and p_val_strict < 0.05 else "FAIL"
    
    print(f"Mean Real: {mean_real_strict:.4f}")
    print(f"Mean Random: {mean_rand_strict:.4f}")
    print(f"Difference: {diff_strict:.4f}")
    print(f"P-Value: {p_val_strict:.6f}")
    print(f"Result: {result_strict}")
    
    report.append({
        "Test": "STRICT FALSIFICATION",
        "Mean_Real": mean_real_strict,
        "Difference": diff_strict,
        "P_Value": p_val_strict,
        "Sonuç": result_strict
    })
    
    # ========== STEP 6: MULTI-SEED ROBUSTNESS ==========
    print(f"\n[STEP 6] MULTI-SEED ROBUSTNESS TEST")
    print("-"*80)
    
    multi_seed_results = []
    for s in SEEDS:
        real_s = []
        for r in top_recipes[:20]:
            subset = df[df['recipe_id'] == r]
            if len(subset) >= 20:
                sample = subset.sample(20, random_state=s)
                score = calculate_strict_score(sample)
                real_s.append(score)
        
        random_s = [calculate_strict_score(df.sample(20, random_state=s+i)) 
                    for i in range(len(real_s))]
        
        mean_real_s = np.mean(real_s)
        mean_rand_s = np.mean(random_s)
        diff_s = mean_real_s - mean_rand_s
        _, p_val_s = stats.ttest_ind(real_s, random_s, equal_var=False)
        
        pass_fail = "PASS" if diff_s > 0.1 and p_val_s < 0.05 else "FAIL"
        
        print(f"Seed {s}: Diff={diff_s:.4f}, P={p_val_s:.6f}, {pass_fail}")
        
        multi_seed_results.append({
            "Seed": s,
            "Difference": diff_s,
            "P_Value": p_val_s,
            "Sonuç": pass_fail
        })
    
    # Adversarial Corruption Test
    print(f"\nAdversarial Test (20% Corruption):")
    df_corrupt = df.copy()
    n_corrupt = int(len(df) * CORRUPTION_RATIO)
    corrupt_indices = df.sample(n_corrupt, random_state=CORRUPTION_SEED).index
    shuffled_recipes = df.loc[corrupt_indices, 'recipe_id'].sample(frac=1, random_state=CORRUPTION_SEED).values
    df_corrupt.loc[corrupt_indices, 'recipe_id'] = shuffled_recipes
    
    adv_real = []
    for r in top_recipes[:20]:
        subset = df_corrupt[df_corrupt['recipe_id'] == r]
        if len(subset) >= 20:
            sample = subset.sample(min(20, len(subset)), random_state=CORRUPTION_SEED)
            if len(sample) >= 2:
                score = calculate_strict_score(sample)
                adv_real.append(score)
    
    adv_random = [calculate_strict_score(df_corrupt.sample(20, random_state=CORRUPTION_SEED+i)) 
                  for i in range(len(adv_real))]
    
    mean_adv_real = np.mean(adv_real) if adv_real else 0
    mean_adv_rand = np.mean(adv_random) if adv_random else 0
    diff_adv = mean_adv_real - mean_adv_rand
    
    adv_result = "PASS (degraded)" if diff_adv < 0.1 else "FAIL (no degradation)"
    print(f"Corrupted: Diff={diff_adv:.4f}, {adv_result}")
    
    all_seeds_pass = all(r['Sonuç'] == 'PASS' for r in multi_seed_results)
    multi_final = "PASS" if all_seeds_pass and "degraded" in adv_result else "FAIL"
    
    report.append({
        "Test": "MULTI-SEED ROBUSTNESS",
        "Seed_Results": multi_seed_results,
        "Adversarial": adv_result,
        "Sonuç": multi_final
    })
    
    # ========== STEP 7: SEMANTIC OPERATOR CLUSTERING ==========
    print(f"\n[STEP 7] SEMANTIC OPERATOR-BASED CLUSTERING")
    print("-"*80)
    
    df['op_signature'] = df['response'].apply(get_operator_signature)
    sig_counts = Counter(df['op_signature'])
    valid_sigs = [sig for sig, count in sig_counts.items() if count >= 10]
    top_sigs = sorted(valid_sigs, key=lambda x: sig_counts[x], reverse=True)[:TOP_RECIPES]
    
    clustering_scores = []
    for sig in top_sigs:
        subset = df[df['op_signature'] == sig].sample(10, random_state=42)
        score = calculate_consistency_score(subset)
        clustering_scores.append(score)
    
    random_scores_cluster = [calculate_consistency_score(df.sample(10, random_state=300+i)) 
                             for i in range(len(clustering_scores))]
    
    mean_cluster_real = np.mean(clustering_scores)
    mean_cluster_rand = np.mean(random_scores_cluster)
    diff_cluster = mean_cluster_real - mean_cluster_rand
    t_stat_cluster, p_val_cluster = stats.ttest_ind(clustering_scores, random_scores_cluster, equal_var=False)
    
    clustering_result = "PASS" if diff_cluster > 0.1 and p_val_cluster < 0.05 else "FAIL"
    
    print(f"Mean Operator-based: {mean_cluster_real:.4f}")
    print(f"Mean Random: {mean_cluster_rand:.4f}")
    print(f"Difference: {diff_cluster:.4f}")
    print(f"T-Stat: {t_stat_cluster:.2f}, P-Value: {p_val_cluster:.6f}")
    print(f"Result: {clustering_result}")
    
    report.append({
        "Test": "SEMANTIC CLUSTERING",
        "Mean_Real": mean_cluster_real,
        "Difference": diff_cluster,
        "P_Value": p_val_cluster,
        "Sonuç": clustering_result
    })
    
    # ========== STEP 8: FINAL REPORT ==========
    print(f"\n{'='*80}")
    print("FINAL CONSOLIDATED REPORT")
    print("="*80)
    
    print(f"\nTest                           | Sonuç")
    print("-"*80)
    for entry in report:
        test_name = entry['Test']
        result = entry.get('Sonuç', 'N/A')
        print(f"{test_name:<30} | {result}")
    
    # Final Decision
    test_results = [entry.get('Sonuç') for entry in report if 'Sonuç' in entry]
    critical_tests = ['FALSIFICATION', 'STRICT FALSIFICATION', 'MULTI-SEED ROBUSTNESS', 'SEMANTIC CLUSTERING']
    critical_results = [entry.get('Sonuç') for entry in report if entry['Test'] in critical_tests]
    
    final_decision = "PASS" if all(r == "PASS" or r == "TAMAMLANDI" or r == "MIXED" for r in critical_results) else "FAIL"
    
    print(f"\n{'='*80}")
    print(f"FINAL DECISION: SYSTEM VERIFIED: {final_decision}")
    print(f"End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    run_pipeline()
