(function() {
gamesoup.namespace('gamesoup.games.dialogHandlers');

var gs = gamesoup;
var mod = gamesoup.games.dialogHandlers;

mod.ConfigureObject = Class.create({
	initialize: function(node, options) {
		this._node = $(node);
		this._objectID = this._node.getAttribute('objectID');
		this._options = {objectID: this._objectID};
		Object.extend(this._options, options);
		this._nameInput = this._node.down('input[type="text"].object-name');
		// Prepare parameters
		this._builtIns = this._node.select('.built-in').collect(this.addBuiltIn.bind(this));
		this._refs = this._node.select('.ref').collect(this.addRef.bind(this));
		this._factories = this._node.select('.factory').collect(this.addFactory.bind(this));
		// Done button
		this._doneButton = this._node.down('.submit-row input[type=button]');		
		// Event handlers
		this._nameInput.observe('change', this.saveName.bind(this));
		this._doneButton.observe('click', function() {this._node.fire('handler:done')}.bind(this));
	},
	release: function() {
		this._builtIns.invoke('release');
		this._refs.invoke('release');
		this._factories.invoke('release');
		this._doneButton.stopObserving();
		this._node.stopObserving();
	},
	addBuiltIn: function(node) {
	    // Built-in parameters have an interface name ending with an
	    // an exlamantion mark (!). For example, String!. The corresponding
	    // JavaScript parameter class goes by the same name, minus
	    // the !.
	    var interfaceName = node.getAttribute('interface').sub(/\!/, '');
		var ParamClass = gamesoup.games.parameters[interfaceName];
		return new ParamClass(node, this._options);
	},
	addRef: function(node) {	    
	    return new gamesoup.games.parameters.Reference(node, this._options);
	},
	addFactory: function(node) {
	    return new gamesoup.games.parameters.FactoryReference(node, this._options);
	},
	saveName: function(event) {
	    var url = gs.utils.makeURL('updateObjectName', this._options);
	    new Ajax.Request(url, {
	        method: 'post',
	        postBody: 'name=' + this._nameInput.getValue(),
	        onSuccess: function() {this._node.fire('assembler:systemChanged');}.bind(this)
	    });
	}
})
gs.tracerize('ConfigureObject', mod.ConfigureObject);


})();
