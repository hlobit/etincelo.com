/* eslint-disable */

// // details in https://css-tricks.com/using-netlify-forms-and-netlify-functions-to-build-an-email-sign-up-widget
const fetch = require('node-fetch')
const base64 = require('base-64');
const CryptoJS = require("crypto-js");
const {
  MAILCHIMP_USERNAME,
  MAILCHIMP_API_KEY,
  MAILCHIMP_DATA_CENTER,
  MAILCHIMP_LIST_ID
} = process.env

exports.handler = async event => {
  try {
    const { email } = JSON.parse(event.body);
    const subscriber = {
      email_address: email,
      status: 'subscribed',
    };
    const creds = `${MAILCHIMP_USERNAME}:${MAILCHIMP_API_KEY}`;
    const updateResponse = await fetch(
      `https://${MAILCHIMP_DATA_CENTER}.api.mailchimp.com/3.0/lists/${MAILCHIMP_LIST_ID}/members/${CryptoJS.MD5(email).toString()}`,
      {
        method: 'PUT',
        headers: {
          Accept: '*/*',
          'Content-Type': 'application/json',
          Authorization: `Basic ${base64.encode(creds)}`,
        },
        body: JSON.stringify(subscriber),
      }
    );
    const updateData = await updateResponse.json();
    console.log(updateData);
    if (updateResponse.ok) {
      return {
        statusCode: 200,
        body: JSON.stringify({
          msg: "You've signed up to the mailing list!",
          detail: updateData,
        }),
      };
    };
    const insertResponse = await fetch(
      `https://${MAILCHIMP_DATA_CENTER}.api.mailchimp.com/3.0/lists/${MAILCHIMP_LIST_ID}/members/`,
      {
        method: 'POST',
        headers: {
          Accept: '*/*',
          'Content-Type': 'application/json',
          Authorization: `Basic ${base64.encode(creds)}`,
        },
        body: JSON.stringify(subscriber),
      }
    );
    const insertData = await insertResponse.json();
    console.log(insertData);
    if (!insertResponse.ok) {
      // NOT res.status >= 200 && res.status < 300
      return { statusCode: insertData.status, body: insertData.detail };
    }
    return {
      statusCode: 200,
      body: JSON.stringify({
        msg: "You've signed up to the mailing list!",
        detail: insertData,
      }),
    };
  } catch (err) {
    console.log(err); // output to netlify function log
    return {
      statusCode: 500,
      body: JSON.stringify({ msg: err.message }), // Could be a custom message or object i.e. JSON.stringify(err)
    };
  };
}
