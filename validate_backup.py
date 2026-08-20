from dataclasses import dataclass
from pathlib import Path
import gzip
import sys

@dataclass
class ValidationResult:
    check: str
    status: str
    message: str

# ↓ VALIDATION FUNCTIONS ↓

# Checks if the file exists, if the path is a file, if the file is empty, or 
# if the correct extension is used.
def validate_file(path: Path) -> list[ValidationResult]:
    results = []

    if not path.exists():
        results.append(ValidationResult(
            check="file_exists",
            status="FAIL",
            message="File does not exist",
        ))
        return results

    results.append(ValidationResult(
        check="file_exists",
        status="PASS",
        message="File exists",
    ))

    if not path.is_file():
        results.append(ValidationResult(
            check="is_file",
            status="FAIL",
            message="Path exists but it is not a file"
        ))
        return results

    results.append(ValidationResult(
        check="is_file",
        status="PASS",
        message="Path is a file",
    ))

    if path.stat().st_size == 0:
        results.append(ValidationResult(
            check="file_not_empty",
            status="FAIL",
            message="File is empty"
        ))
    else:
        results.append(ValidationResult(
            check="file_not_empty",
            status="PASS",
            message=f"File is not empty ({path.stat().st_size} bytes)",
    ))

    if not path.name.endswith(".sql.gz"):
        results.append(ValidationResult(
            check="expected_extension",
            status="WARNING",
            message="File does not end with .sql.gz"
        ))
    else:
        results.append(ValidationResult(
            check="expected_extension",
            status="PASS",
            message="File extension is .sql.gz",
        ))

    return results

# Checks if the gzip file is not compressed, incomplete/interrupted, or corrupted.
def validate_gzip(path: Path) -> ValidationResult:
    try:
        with gzip.open(path, "rb") as file:
            while file.read(1024 * 1024):
                pass

        return ValidationResult(
            check="gzip_integrity",
            status="PASS",
            message="GZIP archive is valid",
        )
    except (gzip.BadGzipFile, EOFError, OSError) as error:
        return ValidationResult(
            check="gzip_integrity",
            status="FAIL",
            message=f'GZIP archive is invalid: {error}'
        )


# Checks if the GZIP file contains a PostgreSQL SQL dump by looking for its dump marker
def validate_sql_dump(path: Path) -> ValidationResult:
    try: 
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:

            content = file.read(100_000)
            if "-- PostgreSQL database dump" in content:
                return ValidationResult(
                    check="file_is_sql_dump",
                    status="PASS",
                    message="File is an sql dump"
                )
            return ValidationResult(
                check="file_is_sql_dump",
                status="FAIL",
                message="SQL dump marker not found"
            )

        
    except OSError as error:
        return ValidationResult(
            check="file_is_sql_dump",
            status="FAIL",
            message=f"Unable to inspect SQL dump content: {error}"
        )

def validate_expected_tables(path: Path) -> ValidationResult:

    expected_tables = {
        "users",
        "posts",
        "topics",
        "categories",
        "groups",
        "user_profiles",
        "topic_users",
        "post_actions",
        "site_settings",
        "uploads",
    }
    found_tables = set()

    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:
            for line in file:
                for table in expected_tables:
                    if f"CREATE TABLE public.{table}" in line:
                        found_tables.add(table)
                        #print(f"{table} FOUND")
                if expected_tables == found_tables:
                    break

    except (gzip.BadGzipFile, EOFError, OSError) as error:
        return ValidationResult(
            check="expected_tables_found",
            status="FAIL",
            message=f"Could not inspect expected tables: {error}",
        )          

    missing_tables = expected_tables.difference(found_tables)

    if len(missing_tables) == 0:
        return ValidationResult(
            check="expected_tables_found",
            status="PASS",
            message="All expected tables are found",
        )
    elif len(missing_tables) == len(expected_tables):
        return ValidationResult(
            check="expected_tables_found",
            status="FAIL",
            message=f"All {len(missing_tables)} expected tables not found: {missing_tables}",
        )
    else:
        return ValidationResult(
            check="expected_tables_found",
            status="WARNING",
            message=f"{len(missing_tables)} expected tables not found: {missing_tables}"
        )
    

# ↓ VALIDATION RESULTS ↓

def get_overall_status(results: list[ValidationResult]) -> str:
    statuses = [result.status for result in results]

    if "FAIL" in statuses:
        return "FAIL"

    if "WARNING" in statuses:
        return "WARNING"

    return "PASS"

def print_report(path: Path, results: list[ValidationResult]) -> None:
    print()
    print("VOCALE Discourse Backup Validation")
    print(f"Backup Checked: {path}")
    print()

    print(f"{'CHECK':<22} {'STATUS':<9}")
    print("--------------------------------------------------------------------------------------|")
    for result in results:
        print(f"{result.check:<22} {result.status:<9} {result.message}")
            
    print()
    print(f"Overall Status: {get_overall_status(results)}")
    print()

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python validate_backup.py /path/to/discourse_backup.sql.gz")
        sys.exit(1)

    backup_path = Path(sys.argv[1])
    results: list[ValidationResult] = []

    validate_file_result = validate_file(backup_path)
    results.extend(validate_file_result)

    if get_overall_status(validate_file_result) != "FAIL":

        validate_gzip_result = validate_gzip(backup_path)
        results.append(validate_gzip_result)

        if validate_gzip_result.status != "FAIL":
            validate_sql_dump_result = validate_sql_dump(backup_path)
            results.append(validate_sql_dump_result)

            if validate_sql_dump_result.status != "FAIL":
                validate_expected_tables_result = validate_expected_tables(backup_path)
                results.append(validate_expected_tables_result)

    print_report(backup_path, results)

    if get_overall_status(results) == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()