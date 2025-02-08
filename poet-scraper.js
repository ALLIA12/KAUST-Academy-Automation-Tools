const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

// Helper function for delay
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function scrapeVerses(page) {
    return await page.evaluate(() => {
        const verses = [];
        const versesElements = document.querySelectorAll('#poem_content h3');

        versesElements.forEach(element => {
            // Clean up the verse text by removing extra spaces and getting text content
            let verse = element.textContent.trim();
            // Some verses might have highlighted words (mosahma_highlight), but we want the full text
            verses.push(verse);
        });

        // Get poem metadata
        const metadataDiv = document.querySelector('.tips.row.content');
        const metadata = {
            type: '',
            topic: '',
            meter: '',
            rhyme: ''
        };

        if (metadataDiv) {
            const links = metadataDiv.querySelectorAll('a');
            links.forEach(link => {
                const href = link.getAttribute('href');
                const text = link.textContent.trim();

                if (href.includes('Type-')) {
                    metadata.type = text;
                } else if (href.includes('Poems-Topics-')) {
                    metadata.topic = text;
                } else if (href.includes('sea-')) {
                    metadata.meter = text.replace('بحر ', '');
                } else if (href.includes('q-')) {
                    metadata.rhyme = text.trim();
                }
            });
        }

        return {
            verses,
            metadata
        };
    });
}

async function scrapePoemsFromPage(page) {
    const poems = await page.evaluate(() => {
        const poemElements = document.querySelectorAll('.content.row.bb.bb-none-1 .record');

        return Array.from(poemElements).map(element => {
            const titleElement = element.querySelector('a.float-right');
            const metadataElement = element.querySelector('.text-data');

            if (titleElement && metadataElement) {
                const text = metadataElement.textContent;
                const topicMatch = text.match(/قصيدة\s+([^\s]+)/);
                const meterMatch = text.match(/من\s+([^\s]+)/);
                const versesMatch = text.match(/عدد ابياتها\s+(\d+)/);

                return {
                    title: titleElement.textContent.trim(),
                    url: titleElement.getAttribute('href'),
                    topic: topicMatch ? topicMatch[1] : '',
                    meter: meterMatch ? meterMatch[1] : '',
                    versesCount: versesMatch ? parseInt(versesMatch[1]) : 0
                };
            }
            return null;
        }).filter(Boolean);
    });

    // For each poem, visit its page and get verses
    const baseUrl = 'https://www.aldiwan.net/';
    for (let i = 0; i < poems.length; i++) {
        const poem = poems[i];
        try {
            const poemUrl = new URL(poem.url, baseUrl).href;
            await page.goto(poemUrl, { waitUntil: 'networkidle0' });
            await delay(1000); // Add small delay between poems

            const { verses, metadata } = await scrapeVerses(page);
            poem.verses = verses;
            poem.fullMetadata = metadata;

            console.log(`  - Scraped poem: ${poem.title} (${verses.length} verses)`);
        } catch (error) {
            console.error(`  - Error scraping poem ${poem.title}:`, error.message);
            poem.verses = [];
            poem.error = error.message;
        }
    }

    return poems;
}

async function scrapePoets() {
    console.log('Starting the scraping process...');

    const browser = await puppeteer.launch({
        headless: "new",
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        console.log('Browser launched successfully');
        const page = await browser.newPage();

        // Set longer timeout for navigation
        page.setDefaultNavigationTimeout(60000);

        // Navigate to the poets page
        console.log('Navigating to the website...');
        await page.goto('https://www.aldiwan.net/cat-poets-pre-islamic-period', {
            waitUntil: 'networkidle0'
        });

        console.log('Page loaded, starting to extract data...');

        // Extract poets information
        const poets = await page.evaluate(() => {
            const poetElements = document.querySelectorAll('.col-lg-4.col-md-6.col-12');

            return Array.from(poetElements).map(element => {
                const nameElement = element.querySelector('.h3');
                const profileLink = element.querySelector('a[href]');
                const imageElement = element.querySelector('img');

                return {
                    name: nameElement ? nameElement.textContent.trim() : '',
                    profileUrl: profileLink ? profileLink.getAttribute('href') : '',
                    imageUrl: imageElement ? imageElement.getAttribute('src') : '',
                    handle: element.querySelector('.text-slug') ?
                        element.querySelector('.text-slug').textContent.trim() : ''
                };
            });
        });

        console.log(`Found ${poets.length} poets. Starting to collect their poems...`);

        // For each poet, visit their page and scrape poems
        const baseUrl = 'https://www.aldiwan.net/';
        const outputDir = path.join(__dirname, 'output');
        await fs.mkdir(outputDir, { recursive: true });

        for (let i = 0; i < poets.length; i++) {
            const poet = poets[i];
            console.log(`\nProcessing poet ${i + 1}/${poets.length}: ${poet.name}`);

            try {
                const poetUrl = new URL(poet.profileUrl, baseUrl).href;
                await page.goto(poetUrl, { waitUntil: 'networkidle0' });
                await delay(2000);

                const poems = await scrapePoemsFromPage(page);
                poet.poems = poems;

                console.log(`Found and scraped ${poems.length} poems for ${poet.name}`);

                // Save progress after each poet
                await fs.writeFile(
                    path.join(outputDir, 'pre-islamic-poets-progress.json'),
                    JSON.stringify(poets, null, 2),
                    'utf-8'
                );

            } catch (error) {
                console.error(`Error processing poet ${poet.name}:`, error.message);
                poet.poems = [];
                poet.error = error.message;
            }
        }

        // Save the final results to a JSON file
        const outputPath = path.join(outputDir, 'pre-islamic-poets.json');
        await fs.writeFile(
            outputPath,
            JSON.stringify(poets, null, 2),
            'utf-8'
        );

        console.log(`\nSuccessfully scraped ${poets.length} poets and their poems`);
        console.log(`Data has been saved to ${outputPath}`);

    } catch (error) {
        console.error('An error occurred:', error);
    } finally {
        await browser.close();
        console.log('Browser closed');
    }
}

// Run the scraper
scrapePoets().catch(console.error);