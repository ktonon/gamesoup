/*
 * Type: TextInput
 * For entering text.
 */
gamesoup.library.types.TextInput = Class.create(gamesoup.library.types.BaseType);

/*****************************************************************************/
/*                             Interface Methods                             */
/*****************************************************************************/
gamesoup.library.types.TextInput.addMethods({
    
    /*---------------------------------------->                       Clearable
     * clear()
     * 
     * Clear the content of this object.
     */                                                               /* vVv */
    clear: function() {
        this._inputNode.setValue('');
    },                                                                /* ^A^ */

    /*---------------------------------------->                       Focusable
     * focus()
     * 
     * Give focus to the object. Input messages from the keyboard and mouse will go directly to this object after focus is called.
     */                                                               /* vVv */
    focus: function() {
        this._inputNode.focus();
    },                                                                /* ^A^ */

    /*---------------------------------------->                        Readable
     * read() : String!
     * 
     * Read this content of this object.
     */                                                               /* vVv */
    read: function() {
        return this._inputNode.getValue();
    },                                                                /* ^A^ */

    /*---------------------------------------->                        Writable
     * write(item : [])
     * 
     * Write a value to the content of this object.
     */                                                               /* vVv */
    write: function(item) {
        this._inputNode.setValue(item);
    }                                                                 /* ^A^ */

});

/*****************************************************************************/
/*                                Engine Hooks                               */
/*           These methods are called by the gamesoup match engine.          */
/*                         Do not call them yourself!                        */
/*                    They are called in the order shown.                    */
/*****************************************************************************/
gamesoup.library.types.TextInput.addMethods({ 
    
    /*
     * Extend the DOM and apply styling.
     */                                                               /* vVv */
    render: function() {
        t = new Template('<input type="text" style="width: 100%; height: 100%; font-size: #{size}px" />');
        var s = (this._height / 2).round();
        this._node.insert({bottom: t.evaluate({size: s})});
        this._inputNode = this._node.down('input[type=text]');
    },                                                                /* ^A^ */
    
    /*
     * Perform custom initialization.
     */                                                               /* vVv */
    register: function() {
        
    },                                                                /* ^A^ */

    /*
     * Perform custom take-down.
     */                                                               /* vVv */
    unregister: function() {
        this._inputNode.disable();
    }                                                                 /* ^A^ */    
});

/*****************************************************************************/
/*                           Implementation Methods                          */
/*                     Do not use outside of this module!                    */
/*****************************************************************************/
gamesoup.library.types.TextInput.addMethods({
    // Helper methods go here...
});