from dataclasses import dataclass
from pathlib import Path
import gzip
import sys

@dataclass
class ValidationResult:
    check: str
    status: str
    message: str

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
            message=f"GZIP archive is invalid: \"{error}\""
        )

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

    print(f"{'CHECK':<22} {'STATUS':<8}")
    print("----------------------------------------------------------------------|")
    for result in results:
        print(f"{result.check:<22} {result.status:<8} {result.message}")
            
    print()
    print(f"Overall Status: {get_overall_status(results)}")
    print()

def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python validate_backup.py /path/to/discourse_backup.sql.gz")
        sys.exit(1)

    backup_path = Path(sys.argv[1])
    results = validate_file(backup_path)
    results.append(validate_gzip(backup_path))
    print_report(backup_path, results)

    if get_overall_status(results) == "FAIL":
        sys.exit(1)

if __name__ == "__main__":
    main()