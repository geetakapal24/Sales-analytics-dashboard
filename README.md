# 📊 Sales Analytics Dashboard

An interactive sales analytics application built with Python to help users analyze sales performance, track profits, identify trends, and compare product and regional performance using their own sales datasets.

## 🚀 Project Overview

Businesses generate sales data in different formats, such as CSV and Excel. Analyzing this data manually can be time-consuming.

This project simplifies the process by allowing users to upload their sales data and explore important business insights through interactive charts, key performance indicators (KPIs), and filters.

## ✨ Features

- **Flexible Data Upload:** Upload sales datasets in CSV or Excel format.
- **Data Cleaning:** Handle missing values, duplicate records, and inconsistent data.
- **Dynamic Column Mapping:** Map uploaded dataset columns to the fields required for analysis.
- **Sales Performance Analysis:** Calculate total sales, total profit, profit margin, and average order value.
- **Interactive Filters:** Filter results by date, category, and region.
- **Visual Analytics:** Explore sales trends, product performance, category distribution, and regional comparisons.
- **Business Insights:** Identify sales growth trends, low-performing products, and profitability concerns.
- **Report Export:** Export processed data and analytical reports for further use.

## 🛠️ Technologies Used

- **Python** — Core programming language
- **Pandas** — Data processing and analysis
- **Streamlit** — Interactive web application interface
- **Plotly** — Interactive charts and visualizations
- **OpenPyXL** — Excel file reading and report generation

## 📂 Project Structure

```text
sales-analytics-dashboard/
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/geetakapal24/sales-analytics-dashboard.git
```

### 2. Navigate to the project directory

```bash
cd sales-analytics-dashboard
```

### 3. Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The application will open in your browser, usually at `http://localhost:8501`.

## 📈 Key Performance Indicators

The dashboard calculates metrics such as:

- Total Sales
- Total Profit
- Profit Margin
- Total Orders
- Average Order Value
- Monthly Sales Growth

The available metrics depend on the columns and data provided in the uploaded file.

## 📊 Visualizations

The dashboard includes visual analysis of:

- Monthly sales trends
- Top- and bottom-performing products
- Sales distribution by category
- Regional and category-level performance

## 📁 Input Dataset

Users can upload their own sales data instead of relying on a single fixed dataset.

The application supports CSV and Excel files, provided they contain suitable columns for the required analysis. Column names may differ between datasets, depending on the available column-mapping options.

## 🎯 Project Objectives

- Reduce manual effort in sales data analysis.
- Make business performance easier to understand.
- Identify trends and potential business opportunities.
- Provide a reusable dashboard for different sales datasets.
- Practice real-world data cleaning, analysis, visualization, and reporting.

## 🔮 Future Improvements

- Add user authentication and role-based access.
- Integrate a database for persistent data storage.
- Support multiple stores and historical datasets.
- Add sales forecasting using machine learning.
- Deploy the application to a cloud hosting platform.
- Provide more advanced profitability and customer analytics.

## 👩‍💻 Author

**Geeta Kapal**

GitHub: [geetakapal24](https://github.com/geetakapal24)

## 📄 License

This project is available for learning and portfolio demonstration. Add a specific open-source license if you intend to grant others formal permission to reuse or modify the code.
