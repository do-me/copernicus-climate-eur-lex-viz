# copernicus-climate-eur-lex-viz

A quick visualization repo for data exports from EUR-LEX.

1. Request data (signed-in) under [this URL](https://eur-lex.europa.eu/search.html?SUBDOM_INIT=ALL_ALL&DTS_SUBDOM=ALL_ALL&sortOneOrder=desc&textScope0=ti-te&DTS_DOM=ALL&sortOne=DD&textScope1=ti-te&lang=en&type=advanced&qid=1770050647082&andText1=climate&andText0=copernicus) (for search terms Climate and Copernicus) as of 3.2.2026 it holds 1272 results
2. Data is very dirty and malformated. The csv is broken as cells are not properly sanitized.
3. Convert the csv to excel, manually clean the columns 'Title', 'Subtitle', 'CELEX number', 'Date of document' (sometimes they are simply shifted by n columns to the right)
4. Run script for preprocessing, deduplicating and filtering
5. Update the index.html here.

Documents included: 

```python
important_eu_document_types = [
    "Treaty",
    "Regulation",
    "Directive",
    "Decision",
    "Delegated regulation",
    "Implementing regulation",
    "Implementing decision",
    "Communication",
    "Joint communication",
    "Strategy",
]
```

Yearly view: 

<img width="1708" height="820" alt="image" src="https://github.com/user-attachments/assets/b424cbb0-b7d5-4156-bb7a-7339e36df2df" />
