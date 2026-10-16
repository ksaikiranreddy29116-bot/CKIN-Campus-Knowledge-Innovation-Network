import unittest
import sys

if __name__ == '__main__':
    print("=" * 60)
    print("Running CKIN Automated Comprehensive Test Suite...")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover('tests')

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED.")
        sys.exit(1)
