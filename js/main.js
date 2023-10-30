/*
For how to build a bundle see:
https://stackoverflow.com/a/52168217/2002452

Briefly put:

	npm init

accept all, then:

npm install '@popperjs/core'
npm install --save-dev browserify esmify
npx browserify -p esmify main.js

*/

import { createPopper } from '@popperjs/core';
global.window.createPopper = createPopper
