# Personal Nabla v2.0: Final Production-Ready Technical Plan

This document outlines the final technical plan for Personal Nabla v2.0, a multi-chain, multi-protocol, and production-ready automated hedging bot.

## 1. n8n Environment Setup

### 1.1. Dependency Management

The n8n Code node requires access to external libraries to parse Solana data. You must enable this in your n8n instance.

**Action:** Set the following environment variable for your n8n instance. This is the exact string required:
`NODE_FUNCTION_ALLOW_EXTERNAL=buffer,@solana/web3.js`

### 1.2. Credential Setup: `MyHyperliquidApi`

_(This section remains unchanged. Create a `Header Auth` credential named `MyHyperliquidApi` with your `walletAddress` and `privateKey`.)_

## 2. Control Panel Google Sheet Schema

The `Control Panel` sheet is updated to include a `protocol` column.

| isActive | chain | protocol | poolAddress | symbol | desiredLeverage | isIsolatedMargin |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| TRUE | base | `aerodrome_v2` | 0x... | AERO | 5 | FALSE |
| TRUE | ethereum | `uniswap_v3` | 0x... | ETH | 5 | FALSE |
| TRUE | solana | `orca` | 7d... | SOL | 10 | TRUE |

### Best Practice: Using a Dropdown for Protocols

To prevent typos and ensure you always enter a valid protocol, it is highly recommended to use Google Sheets' "Data validation" feature to create a dropdown menu for the `protocol` column.

1.  In your Google Sheet, select the range for the dropdowns, starting from the second row to the bottom of the column (e.g., for the `protocol` column, select the range `C2:C`).
2.  Go to the menu and select **Data > Data validation**.
3.  Click **+ Add rule**.
4.  Under "Criteria," choose **"Dropdown."**
5.  Enter the supported protocols as options: `uniswap_v3`, `aerodrome_v2`, `orca`.
6.  Click **Done**.

This will turn the `protocol` column into a dropdown, making the Control Panel easier and safer to use.

## 3. Making the Control Panel "Idiot-Proof"

To prevent user error and unnecessary workflow failures, the following best practices and built-in safety features should be understood.

### 3.1. User-Configured Safety: Data Validation

Using dropdown menus in Google Sheets is the most effective way to prevent typos.

*   **`protocol` Column:** (As previously described) Use a dropdown for `uniswap_v3`, `aerodrome_v2`, `orca`.
*   **`chain` Column:** Create a dropdown for your most-used chains (e.g., `ethereum`, `base`, `solana`).
*   **`isActive` & `isIsolatedMargin` Columns:** Create a dropdown with only two options: `TRUE` and `FALSE`.

This ensures that the data entered into the sheet is always in a format the n8n workflow can understand.

### 3.2. Built-in Safety: Automatic Leverage Adjustment

The bot is designed to protect you from accidentally using too much leverage.

**How it Works:**
1.  The bot reads your `desiredLeverage` from the sheet.
2.  Before executing a trade, it makes an API call to Hyperliquid to get the **official `maxLeverage`** for that specific market.
3.  The bot then uses the **minimum** of those two values.

**Example:**
*   If you enter `20` in the sheet for ETH, but Hyperliquid's max leverage for ETH is `10`, the bot will automatically and safely use `10`.
*   If you enter `5` and the max is `10`, the bot will use your preferred `5`.

This safety check is performed on every single trade, ensuring you never get an error from Hyperliquid for exceeding the leverage limit.

## 4. Optional Enhancement: Auto-Fetching the Trading Symbol

To make the `Control Panel` even easier to use, you can add a Google Apps Script that will automatically fetch and populate the `symbol` column when you enter a `poolAddress`.

### 4.1. How to Install the Script

1.  Open your `Control Panel` Google Sheet.
2.  Go to the menu and select **Extensions > Apps Script**.
3.  A new browser tab will open with the script editor. Delete any placeholder code in the `Code.gs` file.
4.  Copy the entire Javascript code block below and paste it into the editor.
5.  **Crucially, replace the placeholder `YOUR_EVM_ALCHEMY_KEY` with your actual Alchemy API key.**
6.  Click the "Save project" icon (it looks like a floppy disk).
7.  The first time the script runs (i.e., the first time you edit a pool address), Google will ask you to authorize it. You must grant it permission to fetch external URLs and edit your sheet.

### 4.2. The Apps Script Code

This final script correctly fetches symbols for both EVM and Solana pools.

**Additional Setup:** This script requires a free API key from **Helius.dev** for the Solana functionality.

```javascript
// --- CONFIGURATION ---
const EVM_ALCHEMY_KEY = 'OZfSvNcs2kskPPj5Ijvj8'; // Replace with your EVM key
const SOLANA_ALCHEMY_KEY = 'oWbW_HujsV128NiaqaKpB'; // Replace with your Solana key
const HELIUS_API_KEY = '7de793a9-30c0-4f6e-b5f1-b9405b5d4a66'; // Replace with your Helius key

// --- SCRIPT LOGIC ---

function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const range = e.range;
  
  if (sheet.getName() !== 'Control Panel' || range.getColumn() !== 4 || range.getRow() === 1) {
    return;
  }
  
  const row = range.getRow();
  const poolAddress = e.value;
  const chain = sheet.getRange(row, 2).getValue();
  const symbolCell = sheet.getRange(row, 5);
  
  if (!poolAddress || !chain) return;

  symbolCell.setValue('Fetching...');
  try {
    let symbol;
    if (chain === 'solana') {
      symbol = getSplTokenSymbol(poolAddress);
    } else {
      symbol = getErc20Symbol(poolAddress, chain);
    }
    symbolCell.setValue(symbol);
  } catch (err) {
    symbolCell.setValue('Error: ' + err.message);
  }
}

// --- EVM LOGIC ---
function getErc20Symbol(poolAddress, chain) {
  const rpcUrl = `https://eth-${chain}.g.alchemy.com/v2/${EVM_ALCHEMY_KEY}`;
  const token0Address = '0x' + jsonRpcCall(rpcUrl, 'eth_call', [{ to: poolAddress, data: '0x0dfe1681' }, 'latest']).slice(26);
  const token1Address = '0x' + jsonRpcCall(rpcUrl, 'eth_call', [{ to: poolAddress, data: '0xd21220a7' }, 'latest']).slice(26);
  
  const symbol0 = hexToString(jsonRpcCall(rpcUrl, 'eth_call', [{ to: token0Address, data: '0x95d89b41' }, 'latest']));
  const symbol1 = hexToString(jsonRpcCall(rpcUrl, 'eth_call', [{ to: token1Address, data: '0x95d89b41' }, 'latest']));
  
  const stables = ['USDC', 'USDT', 'DAI', 'WETH', 'WBTC'];
  return stables.includes(symbol1.toUpperCase()) ? symbol0 : symbol1;
}

// --- SOLANA LOGIC ---
function getSplTokenSymbol(poolAddress) {
  const alchemyRpcUrl = `https://solana-mainnet.g.alchemy.com/v2/${SOLANA_ALCHEMY_KEY}`;
  const heliusRpcUrl = `https://mainnet.helius-rpc.com/?api-key=${HELIUS_API_KEY}`;
  
  // 1. Get Pool Info to find mint addresses
  const poolInfo = jsonRpcCall(alchemyRpcUrl, 'getAccountInfo', [poolAddress, { encoding: 'base64' }]);
  const poolData = Utilities.base64Decode(poolInfo.value.data[0]);
  
  const tokenMintA = base58Encode(poolData.slice(8, 40));
  const tokenMintB = base58Encode(poolData.slice(40, 72));

  // 2. Get Metadata for both mints from Helius
  const assets = jsonRpcCall(heliusRpcUrl, 'getAssetBatch', [[tokenMintA, tokenMintB]]);
  const symbol0 = assets[0].content.metadata.symbol;
  const symbol1 = assets[1].content.metadata.symbol;
  
  // 3. Return the non-stablecoin symbol
  const stables = ['USDC', 'USDT', 'USDTBS'];
  return stables.includes(symbol1.toUpperCase()) ? symbol0 : symbol1;
}


// --- HELPERS ---
function jsonRpcCall(url, method, params) {
  const options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify({ jsonrpc: '2.0', id: 1, method: method, params: params })
  };
  const response = UrlFetchApp.fetch(url, options);
  const json = JSON.parse(response.getContentText());
  if (json.error) throw new Error(json.error.message);
  return json.result;
}

function hexToString(hex) {
  let str = '';
  for (let i = 2; i < hex.length; i += 2) {
    const byte = parseInt(hex.substr(i, 2), 16);
    if (byte) str += String.fromCharCode(byte);
  }
  return str.trim();
}

function base58Encode(buffer) {
    const alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';
    let x = BigInt('0x' + Array.prototype.map.call(new Uint8Array(buffer), x => ('00' + x.toString(16)).slice(-2)).join(''));
    let output = '';
    while (x > 0) {
        const remainder = x % 58n;
        x = x / 58n;
        output = alphabet[Number(remainder)] + output;
    }
    let leadingZeros = 0;
    for (const byte of buffer) {
        if (byte === 0) leadingZeros++; else break;
    }
    return '1'.repeat(leadingZeros) + output;
}
```

## 5. Workflow Architecture: Multi-Chain & Multi-Protocol

The workflow uses a two-level routing system to handle different chains and different protocols within the EVM ecosystem.

### 3.1. Top-Level Router: By `chain`

This router separates `solana` from EVM-compatible chains (`base`, `ethereum`, etc.).

### 3.2. EVM Sub-Router: By `protocol`

Within the EVM path, a second router separates logic based on the `protocol` column. This allows for handling the unique contract functions of different DEXs.

#### 3.2.1. `uniswap_v3` & `aerodrome_v2` Sub-Paths

Both of these paths are now fully implemented and dynamic.

*   **`uniswap_v3` Path:** This path is highly granular, dynamically fetching `slot0`, `liquidity`, token addresses, token decimals, and `tickSpacing` to ensure compatibility with any Uniswap V3 pool.
*   **`aerodrome_v2` Path:** This path is now fully implemented. As Aerodrome V2 is a fork of Uniswap V3, this path reuses the exact same dynamic data-fetching logic as the Uniswap path, ensuring it can correctly handle any Aerodrome V2 pool.

This ensures that any pool on a supported protocol can be handled correctly without code changes.

### 3.3. Solana Path (`orca`)

The Solana path remains the same as the previous version, dynamically fetching token mints and their decimals to ensure correct price calculations for any Orca Whirlpool.

### 3.4. Error Handling and Reliability

All external `HTTP Request` nodes are configured with **2 retries on failure** and have **"Continue on Fail" enabled**. This prevents a temporary issue with a single pool from halting the entire hedging process for all other positions. Errors are caught and logged to the `Trade Tracker` sheet.

## 4. Final Logic

All paths merge to provide a standardized data object to the `Core Hedging Logic` node, which performs the final capital checks and executes trades on Hyperliquid.

This architecture makes the bot robust, extensible, and truly multi-protocol.