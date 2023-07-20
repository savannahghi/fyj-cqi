import numpy as np
import pandas as pd

import pytest

from apps.labpulse.views import calculate_positivity_rate

"""
Code Analysis

Objective:
The objective of the function is to calculate the positivity rate of a given column in a pandas DataFrame and 
create a new DataFrame with the results. The function also generates a bar chart visualization of the results using the 
bar_chart function.

Inputs:
- df: a pandas DataFrame containing the data to be analyzed
- column_name: the name of the column to be analyzed for positivity rate
- title: a string representing the title of the analysis

Flow:
1. Filter the DataFrame for rows with valid results
2. Calculate the number of tests done
3. Calculate the number of samples positive and negative
4. Calculate the positivity rate
5. Create a new DataFrame with the results
6. Generate a bar chart visualization of the results using the bar_chart function
7. Return the bar chart and the new DataFrame

Outputs:
- fig: a bar chart visualization of the positivity rate results
- positivity_df: a pandas DataFrame containing the positivity rate results

Additional aspects:
- The function rounds the positivity rate to one decimal place
- The new DataFrame is transposed and filtered to remove rows with zero values
- The bar chart visualization is generated using the bar_chart function, which is imported from another module
- The color of the bars in the bar chart is based on the variable names in the DataFrame
"""


class TestCalculatePositivityRate:
    """
    Test suite for the calculate_positivity_rate function.
    """

    @pytest.fixture
    def df(self):
        """
        Fixture that returns a DataFrame with sample data.
        """
        return pd.DataFrame({
            'result': ['Positive', 'Negative', 'Positive', 'Positive']
        })

    def test_valid_results(self, df):
        """
        Tests the function with a DataFrame containing valid results.
        """
        fig, positivity_df = calculate_positivity_rate(df, 'result', 'Test')
        assert positivity_df['values'][0] == 4
        assert positivity_df['values'][1] == 3
        assert positivity_df['values'][2] == 1
        assert positivity_df['values'][3] == 75.0

    def test_column_name_exists(self, df):
        """
        Tests the function with a column name that exists in the DataFrame.
        """
        fig, positivity_df = calculate_positivity_rate(df, 'result', 'Test')
        assert positivity_df['values'][0] == 4
        assert positivity_df['values'][1] == 3
        assert positivity_df['values'][2] == 1
        assert positivity_df['values'][3] == 75.0

    def test_empty_dataframe(self):
        """
        Tests the function with an empty DataFrame.
        """
        df = pd.DataFrame({'result': []})
        fig, positivity_df = calculate_positivity_rate(df, 'result', 'Test')
        assert len(positivity_df) == 0

    def test_column_name_does_not_exist(self, df):
        """
        Tests the function with a column name that does not exist in the DataFrame.
        """
        with pytest.raises(KeyError):
            fig, positivity_df = calculate_positivity_rate(df, 'invalid_column_name', 'Test')

    def test_dataframe_with_null_values(self):
        """
        Tests the function with a DataFrame containing both valid and null values.
        """
        df = pd.DataFrame({
            'result': ['Positive', 'Negative', np.nan, 'Positive']
        })
        fig, positivity_df = calculate_positivity_rate(df, 'result', 'Test')
        assert positivity_df['values'][0] == 3
        assert positivity_df['values'][1] == 2
        assert positivity_df['values'][2] == 1
        assert positivity_df['values'][3] == 66.7
        assert not fig is None

    def test_special_characters_in_title(self, df):
        """
        Tests the function with a title string containing special characters.
        """
        fig, positivity_df = calculate_positivity_rate(df, 'result', 'Test with special characters!')
        assert positivity_df['values'][0] == 4
        assert positivity_df['values'][1] == 3
        assert positivity_df['values'][2] == 1
        assert positivity_df['values'][3] == 75.0
