/**
 * Kvitteringssystem — Google Apps Script
 *
 * OPSÆTNING:
 * 1. Opret et nyt Google Sheet
 * 2. Gå til Extensions → Apps Script
 * 3. Slet alt i Code.gs og indsæt denne kode
 * 4. Klik Deploy → New deployment
 * 5. Vælg type: Web app
 * 6. Execute as: Me
 * 7. Who has access: Anyone
 * 8. Klik Deploy og kopiér URL'en
 * 9. Indsæt URL'en i config.json → apps_script_url
 */

// Kolonnerækkefølge i Sheet
var HEADERS = [
  "Dato", "Indsendt", "Navn", "Type", "Udvalg", "Telefon", "Reg.nr.", "Kontonr.",
  "Butik", "Beskrivelse", "Beløb", "Valuta", "Kategori", "Kommentar", "Kvittering",
  "Status", "Udbetalt dato"
];

// Navn på Drive-mappen til kvitteringsbilleder
var DRIVE_FOLDER_NAME = "Kvitteringer";

/**
 * Håndterer GET-requests — returnerer Sheet-data som JSON (til dashboard).
 */
function doGet(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var lastRow = sheet.getLastRow();

    if (lastRow < 2) {
      return ContentService
        .createTextOutput(JSON.stringify({ status: "ok", headers: HEADERS, rows: [] }))
        .setMimeType(ContentService.MimeType.JSON);
    }

    var data = sheet.getRange(2, 1, lastRow - 1, HEADERS.length).getValues();
    var rows = data.map(function(row, i) {
      var obj = { _row: i + 2 };
      for (var j = 0; j < HEADERS.length; j++) {
        obj[HEADERS[j]] = row[j];
      }
      return obj;
    });

    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok", headers: HEADERS, rows: rows }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Håndterer POST-requests fra Flask-appen.
 * Router mellem kvitteringsupload og statusopdatering.
 */
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);

    // Statusopdatering fra dashboard
    if (data.action === "updateStatus") {
      return updateRowStatus(data);
    }

    // 1. Upload billede til Google Drive
    var imageLink = uploadImageToDrive(data.image_base64, data.image_filename);

    // 2. Tilføj række til Sheet
    appendRow(data, imageLink);

    // 3. Returner succes
    return ContentService
      .createTextOutput(JSON.stringify({ status: "ok", image_link: imageLink }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService
      .createTextOutput(JSON.stringify({ status: "error", message: error.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Opdaterer Status og Udbetalt dato for en specifik række.
 */
function updateRowStatus(data) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var row = data.row;
  var statusCol = HEADERS.indexOf("Status") + 1;
  var udbetalCol = HEADERS.indexOf("Udbetalt dato") + 1;

  if (data.status) {
    sheet.getRange(row, statusCol).setValue(data.status);
  }
  if (data.udbetalt_dato) {
    sheet.getRange(row, udbetalCol).setValue(data.udbetalt_dato);
  }

  return ContentService
    .createTextOutput(JSON.stringify({ status: "ok" }))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Uploader base64-billede til en "Kvitteringer"-mappe i Google Drive.
 * Opretter mappen hvis den ikke findes.
 * Sætter deling til "anyone with link can view".
 * Returnerer link til filen.
 */
function uploadImageToDrive(base64Data, filename) {
  // Find eller opret mappe
  var folders = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  var folder;
  if (folders.hasNext()) {
    folder = folders.next();
  } else {
    folder = DriveApp.createFolder(DRIVE_FOLDER_NAME);
  }

  // Bestem MIME-type fra filnavn
  var mimeType = "image/jpeg";
  if (filename) {
    var ext = filename.split(".").pop().toLowerCase();
    var mimeMap = {
      "jpg": "image/jpeg",
      "jpeg": "image/jpeg",
      "png": "image/png",
      "webp": "image/webp",
      "gif": "image/gif",
      "heic": "image/heic"
    };
    if (mimeMap[ext]) {
      mimeType = mimeMap[ext];
    }
  }

  // Dekod base64 og opret fil
  var bytes = Utilities.base64Decode(base64Data);
  var blob = Utilities.newBlob(bytes, mimeType, filename || "kvittering.jpg");
  var file = folder.createFile(blob);

  // Sæt deling: alle med link kan se
  file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);

  return file.getUrl();
}

/**
 * Tilføjer en række til det aktive Sheet med kvitteringsdata.
 * Opretter headers hvis Sheet er tomt.
 */
function appendRow(data, imageLink) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Opret headers hvis Sheet er tomt
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(HEADERS);
    // Gør headers fed
    sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight("bold");
  }

  // Byg kommentar med evt. OCR-note
  var comment = data.comment || "";
  var note = data.confidence_note || "";
  if (note) {
    comment = comment ? comment + " [OCR: " + note + "]" : "[OCR: " + note + "]";
  }

  // Tidsstempel for indsendelse
  var now = Utilities.formatDate(new Date(), "Europe/Copenhagen", "yyyy-MM-dd HH:mm");

  var row = [
    data.date || "",           // Dato
    now,                       // Indsendt
    data.name || "",           // Navn
    data.payment_type || "",   // Type (udlæg / foreningskort)
    data.udvalg || "",         // Udvalg
    data.phone || "",          // Telefon
    data.reg_nr || "",         // Reg.nr.
    data.konto_nr || "",       // Kontonr.
    data.vendor || "",         // Butik
    data.description || "",    // Beskrivelse
    data.amount || "",         // Beløb
    data.currency || "DKK",    // Valuta
    data.category || "Andet",  // Kategori
    comment,                   // Kommentar
    imageLink,                 // Kvittering (Drive-link)
    "",                        // Status (kasserer udfylder)
    ""                         // Udbetalt dato (kasserer udfylder)
  ];

  sheet.appendRow(row);
}

/**
 * Test-funktion: kan køres fra Apps Script editoren for at verificere opsætning.
 */
function testSetup() {
  var testData = {
    name: "Test Bruger",
    amount: 99.95,
    date: "2026-01-01",
    vendor: "Test Butik",
    category: "Andet",
    currency: "DKK",
    comment: "Testræk — kan slettes",
    confidence_note: "",
    image_base64: Utilities.base64Encode(Utilities.newBlob("test").getBytes()),
    image_filename: "test.txt"
  };

  var imageLink = uploadImageToDrive(testData.image_base64, testData.image_filename);
  appendRow(testData, imageLink);

  Logger.log("Test gennemført! Tjek dit Sheet og Drive-mappen 'Kvitteringer'.");
}
