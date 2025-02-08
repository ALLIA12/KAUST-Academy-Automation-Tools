const puppeteer = require('puppeteer');
const Excel = require('exceljs');
const fs = require('fs');
const path = require('path');


async function scrapeData() {
    const browser = await puppeteer.launch({ headless: false });
    const page = await browser.newPage();
    const url = 'https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/reports-publications/historical-reports/';

    await page.goto(url, { waitUntil: 'networkidle2' });



    // Selector for the start date input
    const startDateSelector = '#startTimePeriod';

    // Wait for the start date input to be available
    await page.waitForSelector(startDateSelector);

    // Set the value of the start date input
    await page.evaluate((selector) => {
        document.querySelector(selector).value = '01-01-2000';
    }, startDateSelector);


    // Selector for the first dropdown
    const firstDropdownSelector = '#marketOrIndices';
    // Selector for the second dropdown
    const secondDropdownSelector = '#entity';

    // Wait for the first dropdown to be available
    await page.waitForSelector(firstDropdownSelector);

    // Get all option values and texts from the first dropdown
    const firstDropdownOptions = await page.evaluate((selector) => {
        const options = Array.from(document.querySelector(selector).options);
        return options.map(option => ({ value: option.value, text: option.textContent }));
    }, firstDropdownSelector);

    // Iterate over each option in the first dropdown
    for (const option of firstDropdownOptions) {
        if (option.value !== '-1') { // Assuming '-1' is the "Select" option to skip
            await page.select(firstDropdownSelector, option.value);
            //console.log(`Set first dropdown to value: ${option.value}, text: ${option.text}`);
            await page.waitForTimeout(1000); // Wait for 1 second

            // Wait for the second dropdown to be available and get its options
            await page.waitForSelector(secondDropdownSelector);
            const secondDropdownOptions = await page.evaluate((selector) => {
                const options = Array.from(document.querySelector(selector).options);
                return options.map(option => ({ value: option.value, text: option.textContent }));
            }, secondDropdownSelector);

            // Iterate over each option in the second dropdown
            for (const option2 of secondDropdownOptions) {
                if (option2.value !== '0') { // Assuming '0' is the "Select Companies" option to skip
                    await page.select(secondDropdownSelector, option2.value);
                    //console.log(`Set second dropdown to value: ${option2.value}, text: ${option2.text}`);


                    await page.waitForTimeout(3000); // Wait for 1 second
                    // Selector for the span containing the number of pages
                    const pagesSelector = '.paginate_of';

                    // Wait for the element to be available
                    await page.waitForSelector(pagesSelector);

                    // Extract and parse the number of pages
                    const numberOfPages = await page.evaluate((selector) => {
                        const text = document.querySelector(selector).innerText;
                        const match = text.match(/of: \s*(\d+)/);
                        return match ? parseInt(match[1], 10) : null;
                    }, pagesSelector);

                    //console.log(`Number of pages: ${numberOfPages}`);
                    // Selector for the "Next" button
                    const nextButtonSelector = '.paginate_button.next';

                    const dataMatrix = [];
                    dataMatrix.push(['Date', 'Open', 'High', 'Low', 'Close', 'Change', '% Change', 'Volume Traded', 'Value Traded(SAR)', 'No.Of Trades'])
                    for (let i = 0; i < numberOfPages; i++) {
                        try {
                            // Wait for the table to be loaded
                            await page.waitForSelector('tbody tr', { timeout: 5000 });

                            // Scrape the table data
                            const tableData = await page.evaluate(() => {
                                const rows = document.querySelectorAll('tbody tr');
                                return Array.from(rows, row => {
                                    const columns = row.querySelectorAll('td');
                                    return Array.from(columns, column => column.innerText.trim());
                                });
                            });

                            for (let row of tableData) {
                                const date = row[0]; // Assuming the date is the first element in the row
                                //console.log(date);
                                if (row.length === 10 && !doesDateExist(date, dataMatrix)) {
                                    dataMatrix.push(row); // Add the row to the data matrix only if the date doesn't exist
                                }
                            }
                            await page.click(nextButtonSelector);
                            // console.log("Clicked the 'Next' button.");
                            // Wait for a short period to allow the page to start loading
                            await page.waitForTimeout(500);
                        } catch (error) {
                            console.error(`Error on page ${i + 1}: ${error.message}`);
                            break;
                        }
                    }
                    // await page.waitForTimeout(3000); // Wait for 1 second
                    // Write data to Excel file
                    const workbook = new Excel.Workbook();
                    const worksheet = workbook.addWorksheet('Data');

                    // Assuming each row in dataMatrix is an array of cell values
                    dataMatrix.forEach((row, index) => {
                        worksheet.addRow(row, 'n');
                    });
                    const directory = path.join(__dirname, 'HistoricalData');
                    fs.mkdirSync(directory, { recursive: true });

                    const firstDropdownText = option.text; // Replace with actual text
                    const secondDropdownText = option2.text; // Replace with actual text
                    const filename = path.join(directory, `${firstDropdownText}_${secondDropdownText}.xlsx`);
                    // Save the file
                    await workbook.xlsx.writeFile(filename);
                    console.log(`File saved: ${filename}`);
                }
            }
        }
    }

    await browser.close();
}
function doesDateExist(date, matrix) {
    return matrix.some(row => row[0] === date);
}

// Function to check if the row is a duplicate
function isDuplicate(row, matrix) {
    return matrix.some(existingRow => JSON.stringify(existingRow) === JSON.stringify(row));
}
scrapeData();
