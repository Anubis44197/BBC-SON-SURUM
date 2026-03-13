from bbc_core.bbc_scalar import BBCScalar, UNSTABLE, DEGENERATE, OmegaOperator

class MatrixOps:
    @staticmethod
    def identity(n):
        return [[BBCScalar(1.0 if i == j else 0.0) for j in range(n)] for i in range(n)]

    @staticmethod
    def matmul(A, B):
        rows_A = len(A)
        cols_A = len(A[0])
        rows_B = len(B)
        cols_B = len(B[0])

        if cols_A != rows_B:
            raise ValueError("Matrix dimensions mismatch")

        result = [[BBCScalar(0.0) for _ in range(cols_B)] for _ in range(rows_A)]
        for i in range(rows_A):
            for j in range(cols_B):
                sum_val = BBCScalar(0.0)
                for k in range(cols_A):
                    sum_val = sum_val + (A[i][k] * B[k][j])
                result[i][j] = sum_val
        return result

    @staticmethod
    def gauss_jordan_inverse(matrix):
        """
        Calculates inverse using Gauss-Jordan elimination with partial pivoting.
        Returns (inverse_matrix, rank, log_info)
        """
        n = len(matrix)
        # Deep copy to augment
        M = [[BBCScalar(x.value, x.state, x.heal_count) for x in row] for row in matrix]
        I = MatrixOps.identity(n)
        
        # Augment M with I -> [M | I]
        aug = [M[i] + I[i] for i in range(n)]
        
        log_info = []
        rank = n

        try:
            for i in range(n):
                # Partial pivoting
                pivot_idx = i
                max_val = abs(aug[i][i].value)
                for k in range(i + 1, n):
                    if abs(aug[k][i].value) > max_val:
                        max_val = abs(aug[k][i].value)
                        pivot_idx = k
                
                if max_val < 1e-9: # Singular or near-singular
                    rank -= 1
                    log_info.append(f"Singularity detected at col {i}, max_val {max_val}")
                    # If singular, we might not be able to fully invert, 
                    # but we continue to process what we can or return early.
                    # For strict inversion, this is a failure.
                    # We will mark it as rank deficient.
                    continue 
                
                # Swap rows
                aug[i], aug[pivot_idx] = aug[pivot_idx], aug[i]
                
                # Normalize pivot row
                pivot = aug[i][i]
                # Check for state issues
                if pivot.state in [UNSTABLE, DEGENERATE]:
                     OmegaOperator.trigger(pivot)
                     log_info.append(f"Healed pivot at {i},{i}")
                     # Re-read value after heal
                     pivot = aug[i][i]

                # If pivot became 0 after heal (rare but possible), skip
                if abs(pivot.value) < 1e-12:
                    rank -= 1
                    continue

                for j in range(i, 2 * n):
                    aug[i][j] = aug[i][j] / pivot
                
                # Eliminate other rows
                for k in range(n):
                    if k != i:
                        factor = aug[k][i]
                        for j in range(i, 2 * n):
                            aug[k][j] = aug[k][j] - factor * aug[i][j]

        except Exception as e:
            log_info.append(f"Gauss-Jordan failed: {str(e)}")
            return None, 0, log_info

        # Extract inverse
        inv = [row[n:] for row in aug]
        
        return inv, rank, log_info

    @staticmethod
    def pseudo_inverse(matrix):
        """
        Simplified pseudo-inverse fallback (A^T * A)^-1 * A^T
        """
        try:
            # Transpose
            rows = len(matrix)
            cols = len(matrix[0])
            T = [[matrix[j][i] for j in range(rows)] for i in range(cols)]
            
            # A^T * A
            ATA = MatrixOps.matmul(T, matrix)
            
            # Inverse of ATA
            ATA_inv, rank, logs = MatrixOps.gauss_jordan_inverse(ATA)
            
            if ATA_inv is None or rank < cols: # Assuming full column rank for left inverse
                 return None, rank, logs + ["Pseudo-inverse failed at ATA inversion"]
                
            # Result = ATA_inv * A^T
            res = MatrixOps.matmul(ATA_inv, T)
            return res, rank, logs + ["Calculated pseudo-inverse"]
        except Exception as e:
             return None, 0, [f"Pseudo-inverse exception: {str(e)}"]

    @staticmethod
    def condition_number(matrix):
        """
        Estimates condition number based on Infinity Norm.
        """
        # Norm(A)
        norm_A = 0
        for row in matrix:
            row_sum = sum(abs(x.value) for x in row)
            if row_sum > norm_A:
                norm_A = row_sum
        
        # Inverse
        inv, rank, _ = MatrixOps.gauss_jordan_inverse(matrix)
        if not inv or rank < len(matrix):
            return float('inf')
            
        # Norm(A^-1)
        norm_Inv = 0
        for row in inv:
            row_sum = sum(abs(x.value) for x in row)
            if row_sum > norm_Inv:
                norm_Inv = row_sum
                
        return norm_A * norm_Inv
