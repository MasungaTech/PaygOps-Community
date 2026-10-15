class TagsField {
    constructor(opts) {
        this.tagify = {}        
        this.inputElement = opts['inputElement']
        this.tagsData = opts['tagsData'];
        this.initTags();
    }

    initTags() {
        this.tagify = new Tagify(this.inputElement, {
            transformTag: this.transformTag,
            enforceWhitelist : true,
            whitelist: this.tagsData,
            originalInputValueFormat: valuesArr => valuesArr.map(item => item.id).join(','),
            dropdown: {
                maxItems: 20, // display max items
                classname: "tags-inline", // Custom inline class
                enabled: 0,
                closeOnSelect: false
            },
            templates : {
                dropdownItem: this.dropdownItem
            }
        });
    }

    transformTag(tagData){
        tagData.class = tagData.style+'-tag';
    }

    dropdownItem(tagData) {
        try{
            return `<div ${this.getAttributes(tagData)} class='tagify__dropdown__item mx-1 badge bg-label-primary ${tagData.style ? tagData.style+'-badge' : ""}' >
                        <span>${tagData.value}</span>
                    </div>`
        }
        catch(err){ console.error(err)}
    }
    
}
