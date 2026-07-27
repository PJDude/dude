#!/bin/bash

dir="$(readlink -m $(dirname "$0"))"
cd $dir/..

VERSION=`cat ./src/version.txt`
VERSION=${VERSION:1:10}
echo VERSION=$VERSION

COMMIT_SHA=${GITHUB_SHA:-xxxxx}
DATE=$(date '+%Y-%m-%d')

replace() {
    local from="$1"
    local to="$2"
    sed "s/${from//\//\\/}/${to//\//\\/}/g"
}

cat io.github.pjdude.DuplicatesDetector.template.yml | replace COMMIT_SHA_TO_REPLACE $COMMIT_SHA | replace VERSION_TO_REPLACE $VERSION > io.github.pjdude.DuplicatesDetector.git.yml
echo io.github.pjdude.DuplicatesDetector.git.yml - done

cat io.github.pjdude.DuplicatesDetector.metainfo.template.xml | replace VERSION_TO_REPLACE $VERSION | replace DATE_TO_REPLACE $DATE > io.github.pjdude.DuplicatesDetector.metainfo.xml
echo io.github.pjdude.DuplicatesDetector.metainfo.xml - done
