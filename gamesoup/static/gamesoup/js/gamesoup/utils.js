(function() {
gamesoup.namespace('gamesoup.utils');

// Aliases for internal use
var gs = gamesoup;
var mod = gamesoup.utils;

gs.assert = function(passCondition, errorMessage) {
    if (!passCondition) {
        console.error(errorMessage);
        console.trace();
    }
}

var _cssNumberPattern = /^(\-?\s*\d+(?:\.\d+)?)\s*([A-Za-z]+)$/; 
mod.cssNumber = function(node, style) {
	node = $(node);
	if (style == 'left') {
    	return node.positionedOffset()[0];
	} else if (style == 'top') {
    	return node.positionedOffset()[1];	    
	} else {
    	return new Number(node.getStyle(style).match(_cssNumberPattern)[1]);	    
	}
}

})();
