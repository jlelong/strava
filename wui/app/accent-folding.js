var accentsMap = {
    "é": "e",
    "ê": "e",
    "è": "e",
    "ë": "e",
    "à": "a",
    "â": "a",
    "ô": "o",
    "ù": "u"
};

function removeAccents(s)
{
    var tok = s.split('');
    var has_accent = false;
    for(i = 0; i < tok.length; i++) {
        var c = tok[i];
        if (accentsMap.hasOwnProperty(c)) {
            tok[i] = accentsMap[c];
            has_accent = true;
        }
    }
    if (has_accent)
        return tok.join('');
    else
        return s;
}
