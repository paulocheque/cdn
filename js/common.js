'use strict';

if (typeof String.prototype.startsWith != 'function') {
    String.prototype.startsWith = function (str){
        return this.slice(0, str.length) == str;
    };
}

if (typeof String.prototype.endsWith != 'function') {
    String.prototype.endsWith = function (str){
        return this.slice(-str.length) == str;
    };
}

if (typeof String.prototype.contains != 'function') {
    String.prototype.contains = function (str) {
        return this.indexOf(str) !== -1;
    };
}

function currentUrl() {
    return encodeURIComponent(window.location);
}

function getQueryVariable(variable, defaultvalue) {
  var query = window.location.search.substring(1);
  var vars = query.split("&");
  for (var i=0;i<vars.length;i++) {
    var pair = vars[i].split("=");
    if (pair[0] == variable) {
      return pair[1];
    }
  }
  return defaultvalue || null;
}

var isMobile = {
    Android: function() {
        return /Android/i.test(navigator.userAgent);
    },
    BlackBerry: function() {
        return /BlackBerry/i.test(navigator.userAgent);
    },
    iOS: function() {
        return /iPhone|iPad|iPod/i.test(navigator.userAgent);
    },
    Windows: function() {
        return /IEMobile/i.test(navigator.userAgent);
    },
    any: function() {
        return (isMobile.Android() || isMobile.BlackBerry() || isMobile.iOS() || isMobile.Windows());
    }
};

function convertCanvasToImage(canvas) {
    var image = new Image()
    // image.crossOrigin = "anonymous"
    image.src = canvas.toDataURL("image/png")
    return image
}

function downloadCanvas(canvasId, buttonId) {
    var button = document.getElementById(buttonId)
    button.addEventListener('click', function (e) {
        // nao funciona dentro de um file.js. Deixar direto no html
        var canvas = document.getElementById(canvasId)
        var dataURL = canvas.toDataURL('image/png')
        button.href = dataURL
    })
    return button
}
