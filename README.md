<h1>Drug Pricing Prediction Model</h1> 

<h3>How to run see the results:</h3>
The final product can be seen by running the `bk_app.py`  (bokeh application) from the command line.  Data will be gathered from sources inside the repository, and should not need to be run independently.  The remaining files are simply for understanding the process I went through to produce the final result and, in the future, for improvement of the product.  At the moment, drug ID numbers are used (as opposed to drug names) in the dropdown menu, because drug ID numbers account for a variety of information that names themselves do not.  The decision to sacrifice readability for data accuracy was made in production of this minimum viable product.  I hope to eliminate the necessity of this sacrifice in subsequent versions.

<h3>Background & Motivation:</h3>  
Pharmaceutical drug spending in the U.S. is on a true upward trend.  Not only is the number of drugs being produced on the rise, but the number of Americans taking those drugs is also increasing.  An accurate projection of drug prices enhances transparency of our healthcare system and allows the public, government, and industry to make more informed decisions regarding their health and finances.

Pharmaceutical companies are not required to publish prices, therefore, we'll be drawing on a dataset from Medicare, who does publish prices.  Lack of price transparency is typically cited as a reason for high prices.  This study looks to shed some light on that, and to create a model that can predict drug prices months out from the current date.

<h3><b>Audience and Purpose:</b></h3>
This project aims to be a tool for pharmacies, pharmacy benefit managers, and other entities who may, for example, be in negotiations regarding pharmaceutical drug prices.  With the objective of providing clearer information regarding the future of drug prices, the steps required to achieve lower drug costs may also be more transparent.

<h3><b>Structure</b></h3>
This project demonstrates methods required to obtain, aggregate, and clean data in order to create predictions of pharmaceutical drug prices via a machine learning model.  The notebooks (and .py file) in this repository are meant to be used in the following order and for the named purposes:

1) `ExploratoryPlots.ipynb` - Exploration of initial data sources (and sources post-merge - notebook 5)
2) `ImportData.ipynb` - Automation of data importation direct from sources
3) `CleanPatentData.ipynb` - Cleaning of patent (FDA) data
4) `CleanPriceData.ipynb` - Cleaning of price (Medicaid/NADAC) data
5) `MergingAllData.ipynb` - Merging of price and patent data (which is subsequently used again in ExploratoryPlots.ipynb)
6) `FeatureEngineering&Encoding.ipynb` - Engineering, and binary encoding, of features
7) `Regression&Plotting.ipynb` - Light formatting and prep for regression, train-test-splitting.  Also contains the custom drug-grouping class for regressions and Bokeh plot code currently in development. This notebook currently makes use of the drug's NDC number (a unique identification number assigned by the FDA.  This number allows us to distinguis between not only drug names, but also delivery methods, strengths, and other factors, where a drug name itself would not necessarily suffice. This decision was made at the sacrifice of some readability. 
8) `Drug_Price_Plots.py` - Bokeh plot application used to view plots of drug prices over time. Final product to include predictions created in notebook 7.  Must be run from the commandline with `bokeh serve bk_app.py --show`

<b>Additionally:</b> 
* `To_Do.ipynb` notebook contains suggestions and initial code for improvements to the minimum viable product.
* `patent.csv`, `exclusivity.csv`, `products.csv` are samples of the patent data from the FDA's orange book
* `plotting_data.csv` contains data required by the Bokeh plot (`Drug_Price_Plots.py`) 
* Other data samples were not included in this repo due to their size (e.g. price data), but can be found at the source link below

<h3>DATA SOURCES:</h3>

Patent data comes from the FDA's Orange Book website, found [here](https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files).

 * Drug price data comes from the [Medicaid.gov website](https://healthdata.gov/dataset/nadac-national-average-drug-acquisition-cost). This dataset comes from surveys produced by the U.S. government to chain and independent pharmacies.  The surveys record the prices paid by retail pharmacies to purchase drug products.  The dataset is updated monthly, with weekly price changes noted.   
    * A data dicationary for the drug price data can be found [here](https://www.medicaid.gov/medicaid-chip-program-information/by-topics/prescription-drugs/ful-nadac-downloads/nadacdatadefinitions.pdf)
    
The following three files come are gathered from a dataset known as the 'Orange Book' (the FDA's dataset on drug approvals).  Source data & the accompanying dictionary can be found [here](https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files').
* `products.txt`: specific information regarding products registered with the FDA
  * Trade name
  * Applicant
  * New Drug Application (NDA) Number
  * Product Number
  * <b>Approval Date</b>
  * Type
* `patent.txt`: patent data as available for each drug ([note](https://www.fda.gov/drugs/development-approval-process-drugs/frequently-asked-questions-patents-and-exclusivity#What_is_the_difference_between_patents_a), this is different from exclusivity).  Columns of interest:
  * New Drug Application (NDA) Number
  * Product Number
  * Patent Number
  * <b>Patent Expire Date</b>
* `exclusivity.txt`: data particular to the exclusive marketing rights granted by the FDA to the drug company for a particular drug.  Columns of interest:
  * New Drug Application (NDA) Number
  * Product Number
  * Exclusivity Code
  * <b>Exclusivity Date</b>

Those in bold are of peak interest.  Although the identified columns are those of clear interest, I'll leave the remaining columns in the datasets as I continue exploring.  

I used the New Drug Application (NDA) Number to join the information from these three files.

The price (NADAC) dataset has 1M+ rows with 12 columns (though maybe only half of those will be useful).  The patent (FDA Orange Book) dataset has roughly 55K rows with 27 columns (half of which could provide predictive power). 

While the datasets don’t line up perfectly, I’ve found that drug names in each of the two datasets can be matched well utilizing Levenshtein distance calculations (via the fuzzywuzzy library) and have been able to create row observations to match up dates jointly with the drug names so that the two datasets are merged on an entirely unique key.  

<h3>Feasibility Analysis (EDA):</h3>
In the Exploratory_Plots notebook, you'll find a plot displaying the price of four metformin-based drugs (a medication widely utilized to manage diabetes).

Following, you will see a plot for the price of ibuprofen over time.  Although the correlation is not quite as strong as that of the metformin variants, there is still a clear path that can be followed (not to mention, an interesting upward trend at the end/beginning of 2018/2019).

These are just two examples of drugs whose prices.  Of necessity, the project will continue to evolve, and apply more features to create better predictions; price over time is insufficient.  The datasets mentioned above will add some features.  Those datasets listed below will provide supplementary questions and features as I develop the predictive model.

<h3>Current Results:</h3> 
Currently, the project draws upon two APIs, though I hope to continue expanding this with more datasets.  I'm currently working on an interactive dashboard where the various types of medications can be selected, and their historical and predicted prices viewed.  Predictions currently have an R-squared of 0.9922 (alternative metrics can be found in the `Regressions&Plotting` notebook), though I anticipate that this may drop as data for more brand_name drugs are introduced.  If this were entirely accurate, it would indicate that the majority of drug prices are really only a factor of the month and year of the date the price is recorded, and whether or not a drug has a therapeutic equivalent.  So far, patent data (i.e. days until the drug patent expires) has not proved to be as predictive as I hoped, though this may be due to the typically long lifespan of drugs.  

I'll continue to update this section as new results are realized.  As mentioned before, other potential areas of improvement listed in the `To_Do.ipynb` notebook.  

<h2><b>Additional Opportunities for Improvement of the Project</b></h2>

<h3><b>Additional Information on the Patent Data</b></h3>
Because I only have 1779 entries for patent dates, I figure I'll need more data for my predictive model.  As it turns out, [patents issued after 1995](http://www.drugsdb.com/blog/how-long-is-a-drug-patent-good-for.html) are valid for 20 years from the patent application filing (assuming maintenance fees are paid every 3.5, 7.5, and 11.5 years after the patent is granted).  From this, I can extrapolate two things: 

* I may be able to extrapolate data for 'Patent_Expire_Date_Text' column based on 'Patent_Submission_Date'.  I'll add this information to a third column instead of filling in the NaN values of the 'Patent_Submission_Date' so I can identify any deviations the results with the actual 'Patent_Expire_Date_Text' information that I imported earlier.
  * Additional factors to consider: 
    * Hatch-Waxman extension: A drug can obtain a patent extension of 5 years to make up the length of the FDA approval process.
    * Pediatric exclusivity extension: drugs tested on children can gain an extra 6 months of patent protection (this can be used twice)
    * Drug reformulations: i.e. turning an drug taken by injection into a nasal spray version, or modifying dosages, can extend a patent for an additional up to 5 years
    * New uses: Drugs whose new uses are discovered can obtain another 3 years of patent protection
    * Orphan drugs (those treating rare diseases) gain an additional 7 years of patent protection (and the FDA can't approve any competing generics during the time)
    * 30-Month Stays: Generics often issue a competing patent, and are sued by the brand-name company.  This initiates a 30-month stay on the FDA approval of the generic.
      * Few drug companies can take advantage of this
    * Most of the methods above can be combined to secure a longer patent
* Any drugs with patent issue dates before 1995 may not be valid for prediction as the law governing these patents apparently changed

I'll evaluate the dates we currently have to see if a pattern is evident, before combining them with new estimations based on the factors above.

<h3><b>Other datasets:</b></h3>

* [Pharmaceutical Preparation Manufacturing - Producer Price Index by Industry](https://fred.stlouisfed.org/series/PCU325412325412)
  * [Breakdown of the above](https://fred.stlouisfed.org/release/tables?rid=46&eid=135301#snid=135309)
    
* [Producer Price Index by Industry: Pharmacies and Drug Stores: Retailing of Prescription Drugs](https://fred.stlouisfed.org/series/PCU4461104461101)
* SEC 10-k/10-q data --> pharma companies' financial data (R&D, Profits, Revenue)
* Pharma stock prices over time (proxy for SEC data?)
* Number of pieces of legislation pertaining to pharmaceuticals (may need sentiment analysis for these to determine if they're pro/contra pharma)
* Number of news stories regarding pharmaceuticals
* Pharmacy Benefit Manager (PBM) stock prices (proxy with pharma stock prices for the cost of pharmaceuticals to consumers)?

<h3><b>Other Information:</b></h3>

A few definitions to keep in mind:
 * A __drug product__ is a finished dosage form, e.g., tablet, capsule, or solution, that contains a drug substance, generally, but not necessarily, in association with one or more other ingredients. 
    * e.g. formulation and composition
 * A __drug substance__ is an active ingredient that is intended to furnish pharmacological activity or other direct effect in the diagnosis, cure, mitigation, treatment, or prevention of disease or to affect the structure or any function of the human body, but does not include intermediates used in the synthesis of such ingredient. 
    * e.g. active ingredient
    
<h3><b>Additional Literature</b></h3>

* [Forbes - Price Transparency: Why are Drug Prices Such a Bitter Pill to Swallow](https://www.forbes.com/sites/joeharpaz/2019/05/17/price-transparency-why-are-drug-prices-such-a-bitter-pill-to-swallow/#61c45298396d)
   
* [NADAC pricing in the real world](https://us.milliman.com/uploadedFiles/insight/2018/NADAC-plus.pdf)

* [Fact Sheet: How much money could Medicare save by negotiating prescription drug prices?](http://www.crfb.org/press-releases/fact-sheet-how-much-money-could-medicare-save-negotiating-prescription-drug-prices)
