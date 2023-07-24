import pandas as pd

import pytest

from apps.labpulse.views import line_chart_median_mean

"""
Code Analysis

Objective:
The objective of the 'line_chart_median_mean' function is to generate a line chart using Plotly Express library that displays the median and mean weekly CD4 count collection for a given dataset.

Inputs:
- df: a pandas DataFrame containing the data to be plotted
- x_axis: a string representing the column name to be used as the x-axis
- y_axis: a string representing the column name to be used as the y-axis
- title: a string representing the title of the chart

Flow:
1. The function makes a copy of the input DataFrame and selects the first 52 rows.
2. It calculates the mean and median of the y-axis column for the selected data.
3. It creates a line chart using Plotly Express with the x-axis, y-axis, and title specified.
4. It adds a horizontal line representing the mean value and an annotation with the mean value.
5. It adds a horizontal line representing the median value and an annotation with the median value.
6. It updates the layout of the chart to adjust the font size and color.
7. It returns the chart as a Plotly div object.

Outputs:
- A Plotly line chart displaying the median and mean weekly CD4 count collection for the input dataset.

Additional aspects:
- The function uses Plotly Express and Plotly offline libraries to generate the chart.
- It sets the font size and color of the chart elements.
- It adds annotations to the chart to display the median and mean values.
- It returns the chart as a Plotly div object to be embedded in a web page.
"""
class TestLineChartMedianMean:
    #  Tests the function with a valid dataframe, x-axis, y-axis and title
    def test_valid_dataframe(self):
        df = pd.DataFrame({'x': [1, 2, 3], 'y': [4, 5, 6]})
        result = line_chart_median_mean(df, 'x', 'y', 'Test Chart')
        assert isinstance(result, str)
        assert 'Test Chart' in result
        assert 'Mean weekly CD4 count collection' in result
        assert 'Median weekly CD4 count collection' in result

    #  Tests the function with a dataframe containing 52 rows
    def test_dataframe_52_rows(self):
        df = pd.DataFrame({'x': range(52), 'y': range(52)})
        result = line_chart_median_mean(df, 'x', 'y', 'Test Chart')
        assert isinstance(result, str)
        assert 'Test Chart' in result
        assert 'Mean weekly CD4 count collection' in result
        assert 'Median weekly CD4 count collection' in result

    #  Tests the function with a dataframe containing more than 52 rows
    def test_dataframe_more_than_52_rows(self):
        df = pd.DataFrame({'x': range(53), 'y': range(53)})
        result = line_chart_median_mean(df, 'x', 'y', 'Test Chart')
        assert isinstance(result, str)
        assert 'Test Chart' in result
        assert 'Mean weekly CD4 count collection' in result
        assert 'Median weekly CD4 count collection' in result

    #  Tests the function with an empty dataframe
    def test_empty_dataframe(self):
        df = pd.DataFrame({'x': [], 'y': []})
        with pytest.raises(ZeroDivisionError):
            line_chart_median_mean(df, 'x', 'y', 'Test Chart')

    #  Tests the function with a dataframe containing only one row
    def test_dataframe_one_row(self):
        df = pd.DataFrame({'x': [1], 'y': [2]})
        result = line_chart_median_mean(df, 'x', 'y', 'Test Chart')
        assert isinstance(result, str)
        assert 'Test Chart' in result
        assert 'Mean weekly CD4 count collection' in result
        assert 'Median weekly CD4 count collection' in result

    #  Tests the function with a dataframe containing only one column
    def test_dataframe_one_column(self):
        df = pd.DataFrame({'x': [1, 2, 3]})
        with pytest.raises(KeyError):
            line_chart_median_mean(df, 'x', 'y', 'Test Chart')
